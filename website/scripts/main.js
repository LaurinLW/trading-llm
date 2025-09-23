import { fetchAccount } from './account';
import { awaitData } from './chart';
import { fetchSettings } from './settings';
import { fetchPostitions } from './positions';
import {awaitDataPortfolioValue, createControls} from './portfolioChart';

await fetchSettings();
await fetchAccount();
setInterval(fetchAccount, 60 * 1000);
await fetchPostitions();
setInterval(fetchPostitions, 60 * 1000);
createControls();
await awaitDataPortfolioValue();
setInterval(awaitDataPortfolioValue, 60 * 1000);
await awaitData();
