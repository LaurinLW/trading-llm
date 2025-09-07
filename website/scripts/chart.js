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
    buySignal: z.boolean(),
    sellSignal: z.boolean(),
  })
);

const mockStockData = {
  labels: ['2025-09-01', '2025-09-02', '2025-09-03', '2025-09-04', '2025-09-05', '2025-09-06'],
  prices: [100, 102, 101, 105, 108, 107],
  buySignals: [false, true, false, false, true, false],
  sellSignals: [false, false, true, false, false, false],
};

async function fetchData() {
  const response = await fetch('http://localhost:8080/stockData');

  if (!response.ok) {
    return mockStockData;
  }

  const data = await response.json();
  const parsedData = StockDataSchema.parse(data);
  console.log(data);
  const returnData = { labels: [], prices: [], buySignals: [], sellSignals: [] };

  parsedData.forEach((item) => {
    returnData.labels.push(item.timestamp);
    returnData.prices.push(item.close);
    returnData.sellSignals.push(item.sellSignal);
    returnData.buySignals.push(item.buySignal);
  });

  return returnData;
}

export async function initChart() {
  const data = await fetchData();

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
  new Chart(ctx, {
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
