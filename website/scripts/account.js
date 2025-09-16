import config from './config.js';

export async function fetchAccount() {
  try {
    const response = await fetch(`${config.BACKEND_URL}/account`);

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    const container = document.getElementsByClassName('account')[0];
    container.innerHTML = `
      <div>
        <h3>Portfolio value: ${data.portfolio_value}$</h3>
        <p>Cash: ${data.cash}$</p>
        <p>Buying power: ${data.buying_power}$</p>
        <p>Long market value: ${data.long_market_value}$</p>
        <p>Short market value: ${data.short_market_value}$</p>
      </div>
    `;
  } catch (error) {
    console.log(error);
    document.getElementsByClassName('account')[0].innerHTML = '<p>Error loading data</p>';
  }
}
