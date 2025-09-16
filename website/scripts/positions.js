import config from './config.js';

export async function fetchPostitions() {
  try {
    const response = await fetch(`${config.BACKEND_URL}/positions`);

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    console.log(data);
    const container = document.getElementsByClassName('positions')[0];
    container.innerHTML = `<h3>Open Positions</h3>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Quantity</th>
            <th>Market Value</th>
            <th>Cost Basis</th>
            <th>Unrealized Profit / Loss</th>
          </tr>
        </thead>
        <tbody>
        ${data
          .map(
            (dataPoint) => `
          <tr>
            <td>${dataPoint.symbol}</td>
            <td>${dataPoint.quantity}</td>
            <td>${dataPoint.market_value}</td>
            <td>${dataPoint.original_cost}</td>
            <td ${dataPoint.unrealized_profit_loss >= 0 ? 'class="positive"' : ''}>${dataPoint.unrealized_profit_loss}</td>
          </tr>`
          )
          .join('')}
        </tbody>
      </table>`;
  } catch (error) {
    console.log(error);
    document.getElementsByClassName('positions')[0].innerHTML = '<p>Error loading data</p>';
  }
}
