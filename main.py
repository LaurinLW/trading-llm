import logging
import os
from dotenv import load_dotenv

from grokClient import GrokAPIClient
from stockClient import StockDataClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    load_dotenv()

    grok_api_key = os.getenv("GROK_API_KEY")
    alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not grok_api_key:
        logger.error("GROK_API_KEY environment variable not set")
        raise ValueError("Please set the GROK_API_KEY environment variable")

    if not alpha_vantage_api_key:
        logger.error("ALPHA_VANTAGE_API_KEY environment variable not set")
        raise ValueError("Please set the ALPHA_VANTAGE_API_KEY environment variable")

    grok_client = GrokAPIClient(api_key=grok_api_key)
    stock_client = StockDataClient(api_key=alpha_vantage_api_key)

    data = stock_client.fetch_minute_data('TSLA')
    if data:
        print("\nStock Data:")
        print(f"Symbol: {data['symbol']}")
        print(f"Timestamp: {data['timestamp']}")
        print(f"Open: {data['open']:.2f}")
        print(f"High: {data['high']:.2f}")
        print(f"Low: {data['low']:.2f}")
        print(f"Close: {data['close']:.2f}")
        print(f"Volume: {data['volume']}\n")

    
    grok_client.chat()

if __name__ == "__main__":
    main()