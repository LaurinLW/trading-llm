import config from './config.js';

export async function fetchSettings() {
  try {
    const response = await fetch(`${config.BACKEND_URL}/settings`);

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();

    const container = document.getElementsByClassName('settings')[0];

    container.innerHTML = `
      <div>
        <h3>Grok Model: ${data.model}</h3>
        <p>Disabled: ${data.disabled_grok}</p>
        <p>Prompt interval: ${data.interval} min</p>
        <p>Paper trading: ${data.paper}</p>
      </div>
    `;
  } catch (error) {
    console.log(error);
    document.getElementsByClassName('settings')[0].innerHTML = '<p>Error loading data</p>';
  }
}
