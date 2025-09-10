import asyncio
import logging
import os
import threading
from dotenv import load_dotenv
from server import Gateway, GrokAPIClient, StockDataClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
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

    gateway = Gateway()
    thread = threading.Thread(target=gateway.run_server, daemon=True)
    thread.start()

    grok_client = GrokAPIClient(api_key=grok_api_key)
    stock_client = StockDataClient(alpaca_api_key, alpaca_secret, "Live", gateway, grok_client)

    await stock_client.handleStream()



if __name__ == "__main__":
    asyncio.run(main())
