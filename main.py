import logging
import os
from dotenv import load_dotenv
from waitress import serve

from grokClient import GrokAPIClient
import grokClient
from stockClient import StockDataClient
from controller import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    grok_api_key = os.getenv("GROK_API_KEY")
    alpaca_api_key = os.getenv("ALPACA_API_KEY")
    alpaca_secret = os.getenv("ALPACA_SECRET")

    if not grok_api_key:
        logger.error("GROK_API_KEY environment variable not set")
        raise ValueError("Please set the GROK_API_KEY environment variable")

    if not alpaca_api_key:
        logger.error("ALPACA_API_KEY environment variable not set")
        raise ValueError("Please set the ALPACA_API_KEY environment variable")

    if not alpaca_secret:
        logger.error("ALPACA_SECRET environment variable not set")
        raise ValueError("Please set the ALPACA_SECRET environment variable")

    grok_client = GrokAPIClient(api_key=grok_api_key)
    stock_client = StockDataClient(alpaca_api_key, alpaca_secret, "Historic")

    app = create_app(stock_client, grok_client)
    serve(app, host="0.0.0.0", port=8080)
    print("Serving app on 0.0.0.0:8080")


if __name__ == "__main__":
    main()
