import Chart from 'chart.js/auto';
import annotationPlugin from 'chartjs-plugin-annotation';
import z from 'zod';
import config from './config.js';

Chart.register(annotationPlugin);

const PortfolioDataSchema = z.array(
  z.object({
    equity: z.number(),
    timestamp: z.string(),
  })
);

export async function awaitDataPortfolioValue() {
  const response = await fetch(`${config.BACKEND_URL}/portfoliovalue`);
  const data = await response.json();
  const chartData = convertData(data);
  await drawChart(chartData);
}

function convertData(data) {
  const parsedData = PortfolioDataSchema.parse(data);
  console.log(data);
  const returnData = { labels: [], values: [] };

  parsedData.forEach((item) => {
    returnData.labels.push(item.timestamp);
    returnData.values.push(item.equity);
  });

  return returnData;
}

let myChart;

async function drawChart(data) {
  if (myChart) {
    myChart.destroy();
  }

  const ctx = document.getElementById('portfolioChart').getContext('2d');
  myChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [
        {
          label: 'Account Value',
          data: data.values,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: false,
          tension: 0.3,
          yAxisID: 'y',
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
          suggestedMax: Math.max(...data.values) * 1.005,
          beginAtZero: false,
          position: 'left',
        },
      },
      layout: {},
      plugins: {
        legend: {
          display: true,
          position: 'top',
        },
      },
    },
  });
}
