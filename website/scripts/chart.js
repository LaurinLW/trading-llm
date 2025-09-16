import Chart from 'chart.js/auto';
import annotationPlugin from 'chartjs-plugin-annotation';
import z from 'zod';

Chart.register(annotationPlugin);

const StockDataSchema = z.array(
  z.object({
    close: z.number(),
    high: z.number(),
    low: z.number(),
    open: z.number(),
    timestamp: z.string(),
    trade_count: z.number(),
    volume: z.number(),
    fivePeriodMovingAverage: z.number(),
    tenPeriodMovingAverage: z.number(),
    sixPeriodRSI: z.number(),
  })
);

const mockStockData = {
  labels: ['2025-09-01', '2025-09-02', '2025-09-03', '2025-09-04', '2025-09-05', '2025-09-06'],
  prices: [100, 102, 101, 105, 108, 107],
  buySignals: [false, true, false, false, true, false],
  sellSignals: [false, false, true, false, false, false],
};

function waitForWebSocketClose(websocket) {
  return new Promise((resolve) => {
    websocket.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      resolve(event);
    };
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      resolve(error);
    };
  });
}

export async function awaitData() {
  const response = await fetch('trading/api/data');
  const initialData = await response.json();
  const initialChartData = convertData(initialData);
  await drawChart(initialChartData);

  const websocket = new WebSocket('wss://' + window.location.host + '/ws');

  websocket.onmessage = async (event) => {
    const data = event.data;
    console.log(data);
    const parsedData = JSON.parse(data);
    console.log(parsedData);
    const chartData = convertData(parsedData);
    await drawChart(chartData);
  };

  await waitForWebSocketClose(websocket);
}

function convertData(data) {
  const parsedData = StockDataSchema.parse(data);
  console.log(data);
  const returnData = { labels: [], prices: [], buySignals: [], sellSignals: [], fivePeriodMovingAverage: [], tenPeriodMovingAverage: [], sixPeriodRSI: [] };

  parsedData.forEach((item) => {
    returnData.labels.push(item.timestamp);
    returnData.prices.push(item.close);
    returnData.sellSignals.push(item.sellSignal);
    returnData.buySignals.push(item.buySignal);
    returnData.fivePeriodMovingAverage.push(item.fivePeriodMovingAverage);
    returnData.tenPeriodMovingAverage.push(item.tenPeriodMovingAverage);
    returnData.sixPeriodRSI.push(item.sixPeriodRSI);
  });

  return returnData;
}

let myChart;

async function drawChart(data) {
  if (myChart) {
    myChart.destroy(); // Destroy existing if it exists
  }
  const annotations = [];

  data.buySignals.forEach((flagSet, index) => {
    if (flagSet) {
      annotations.push({
        type: 'point',
        xValue: data.labels[index],
        yValue: data.prices[index],
        radius: 5,
        backgroundColor: 'rgba(40, 255, 40, 1)',
        display: true,
      });

      annotations.push({
        type: 'label',
        display: true,
        backgroundColor: 'rgba(40, 255, 40, 1)',
        content: 'Buy',
        yAdjust: -25,
        xValue: data.labels[index],
        yValue: data.prices[index],
        font: {
          size: 13,
        },
      });
    }
  });

  data.sellSignals.forEach((flagSet, index) => {
    if (flagSet) {
      annotations.push({
        type: 'point',
        xValue: data.labels[index],
        yValue: data.prices[index],
        radius: 5,
        backgroundColor: 'rgba(255, 40, 40, 1)',
        display: true,
      });

      annotations.push({
        type: 'label',
        display: true,
        backgroundColor: 'rgba(255, 40, 40, 1)',
        content: 'Sell',
        yAdjust: -25,
        xValue: data.labels[index],
        yValue: data.prices[index],
        font: {
          size: 13,
        },
      });
    }
  });

  const ctx = document.getElementById('stockChart').getContext('2d');
  myChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [
        {
          label: 'Stock Price',
          data: data.prices,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: false,
          tension: 0.3,
          yAxisID: 'y',
        },
        {
          label: '5 period moving Average',
          data: data.fivePeriodMovingAverage,
          borderColor: 'rgba(68, 255, 0, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: false,
          tension: 0.3,
          yAxisID: 'y',
        },
        {
          label: '10 period moving Average',
          data: data.tenPeriodMovingAverage,
          borderColor: 'rgba(204, 0, 255, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: false,
          tension: 0.3,
          yAxisID: 'y',
        },
        {
          label: '6 period Relative Strength Index',
          data: data.sixPeriodRSI,
          borderColor: 'rgba(255, 0, 0, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: false,
          tension: 0.3,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          title: {
            display: true,
            text: 'Date',
          },
        },
        y: {
          title: {
            display: true,
            text: 'Price (USD)',
          },
          suggestedMax: Math.max(...data.prices) * 1.005,
          beginAtZero: false,
          position: 'left',
        },
        y1: {
          title: {
            display: true,
            text: 'Relative Strength Index',
          },
          suggestedMax: Math.max(...data.sixPeriodRSI) * 1.005,
          beginAtZero: false,
          position: 'right',
        },
      },
      layout: {},
      plugins: {
        legend: {
          display: true,
          position: 'top',
        },
        annotation: {
          annotations: annotations,
        },
      },
    },
  });
}
