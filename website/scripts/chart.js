import Chart from 'chart.js/auto';
import annotationPlugin from 'chartjs-plugin-annotation';
import z from 'zod';
import config from './config.js';

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
  const response = await fetch(`${config.BACKEND_URL}/data`);
  const initialData = await response.json();
  const initialChartData = convertData(initialData);
  await drawChart(initialChartData);

  const websocket = new WebSocket(`${config.WEBSOCKET_URL}`);

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
  const returnData = { labels: [], prices: [], buySignals: [], sellSignals: [], fivePeriodMovingAverage: [], tenPeriodMovingAverage: [], sixPeriodRSI: [], dateChangeIndices: [] };

  let lastDate = null;

  parsedData.forEach((item, index) => {
    const date = new Date(item.timestamp);

    if (lastDate && date.getDay() !== lastDate.getDay()) {
      returnData.dateChangeIndices.push({ index: returnData.labels.length, date: date });
    }

    returnData.labels.push(`${date.getHours()}:${date.getMinutes() === 0 ? "00" : date.getMinutes()}`);
    returnData.prices.push(item.close);
    returnData.sellSignals.push(item.sellSignal);
    returnData.buySignals.push(item.buySignal);
    returnData.fivePeriodMovingAverage.push(item.fivePeriodMovingAverage);
    returnData.tenPeriodMovingAverage.push(item.tenPeriodMovingAverage);
    returnData.sixPeriodRSI.push(item.sixPeriodRSI);

    lastDate = date;
  });

  return returnData;
}

let myChart;

async function drawChart(data) {
  if (myChart) {
    myChart.destroy();
  }

  const annotations = [];

  data.dateChangeIndices.forEach(({ index, date }) => {
    annotations.push({
      type: 'line',
      xMin: index,
      xMax: index,
      borderColor: 'rgba(255,255,255,0.5)',
      borderWidth: 1,
      borderDash: [5, 5],
      display: true,
    });

    annotations.push({
      type: 'label',
      content: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      enabled: true,
      color: 'white',
      xValue: index - 0.175,
      yValue: Math.max(...data.prices) * 1.004,
      font: { size: 12, family: 'Courier New' },
    });
  })

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
      maintainAspectRatio: false,
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
        annotation: { annotations },
        legend: {
          display: true,
          position: 'top',
        },
      },
    },
  });
}
