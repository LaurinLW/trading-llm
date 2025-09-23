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

const INTERVAL_KEY = 'portfolioInterval';

function getCurrentInterval() {
  return localStorage.getItem(INTERVAL_KEY) || 'fifteen';
}

function setCurrentInterval(interval) {
  localStorage.setItem(INTERVAL_KEY, interval);
}

export async function awaitDataPortfolioValue(interval = null) {
  if (interval) {
    setCurrentInterval(interval);
  }
  const currentInterval = getCurrentInterval();
  const response = await fetch(`${config.BACKEND_URL}/portfoliovalue`);
  const data = await response.json();
  const chartData = convertData(data[currentInterval]);
  await drawChart(chartData);
}

export function createControls() {
  const controlsDiv = document.querySelector('.portfolio-controls');
  if (!controlsDiv) return;

  controlsDiv.innerHTML = '';

  const intervals = [
    { key: 'one', label: '1m' },
    { key: 'fifteen', label: '15m' },
    { key: 'hour', label: '1h' },
    { key: 'day', label: '1d' }
  ];

  const currentInterval = getCurrentInterval();

  intervals.forEach(({ key, label }) => {
    const button = document.createElement('button');
    button.textContent = label;
    button.classList.toggle('active', key === currentInterval);
    button.addEventListener('click', () => {
      setCurrentInterval(key);
      awaitDataPortfolioValue(key);
      // Update active class
      document.querySelectorAll('.portfolio-controls button').forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');
    });
    controlsDiv.appendChild(button);
  });
}

// Call createControls when the module loads
createControls();

function convertData(data) {
  const parsedData = PortfolioDataSchema.parse(data);
  console.log(data);
  const returnData = { labels: [], values: [], dateChangeIndices: [] };

  let lastDate = null;

  parsedData.forEach((item, index) => {
    const date = new Date(item.timestamp);
    const currentDate = date.toDateString();

    if (lastDate && currentDate !== lastDate) {
      returnData.dateChangeIndices.push({ index: returnData.labels.length, date: date });
    }

    returnData.labels.push(`${date.getHours()}:${date.getMinutes() === 0 ? "00" : date.getMinutes()}`);
    returnData.values.push(item.equity);

    lastDate = currentDate;
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
      yValue: Math.max(...data.values) * 1.004,
      font: { size: 14, family: 'Courier New' },
    });
  })

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
        annotation: {
          annotations
        },
        legend: {
          display: true,
          position: 'top',
        },
      },
    },
  });
}
