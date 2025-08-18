import logging
from typing import Optional, Dict, Any
import requests

# Set up logging for debugging and error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockDataClient:
    def __init__(self, api_key: str, base_url: str = "https://www.alphavantage.co/query"):
        """
        Initialize the Alpha Vantage API client for stock data.
        
        Args:
            api_key (str): The Alpha Vantage API key.
            base_url (str): The base URL for the Alpha Vantage API.
        """
        self.api_key = api_key
        self.base_url = base_url
        logger.info("StockDataClient initialized")

    def fetch_minute_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch minute-by-minute stock data for a given symbol.
        
        Args:
            symbol (str): The stock symbol (e.g., AAPL).
        
        Returns:
            Optional[Dict[str, Any]]: The latest minute data as a dictionary, or None if the request fails.
        """
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": "1min",
                "apikey": self.api_key,
                "outputsize": "compact"  # Get the most recent data
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "Time Series (1min)" in data:
                latest_time = max(data["Time Series (1min)"].keys())
                latest_data = data["Time Series (1min)"][latest_time]
                result = {
                    "symbol": symbol,
                    "timestamp": latest_time,
                    "open": float(latest_data["1. open"]),
                    "high": float(latest_data["2. high"]),
                    "low": float(latest_data["3. low"]),
                    "close": float(latest_data["4. close"]),
                    "volume": int(latest_data["5. volume"])
                }
                logger.info(f"Received minute data for {symbol}")
                return result
            else:
                logger.warning(f"No valid minute data for {symbol}: {data.get('Note', 'Unknown error')}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON decode error for {symbol}: {e}")
            return None