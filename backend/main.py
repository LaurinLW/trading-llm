import asyncio
import logging
import os
import uvicorn
from dotenv import load_dotenv
from server import GrokAPIClient, StockDataClient, TradingDataClient
from app import app, set_stock_client, send_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    load_dotenv()

    grok_api_key = os.getenv("GROK_API_KEY")
    alpaca_api_key = os.getenv("APCA_API_KEY_ID")
    alpaca_secret = os.getenv("APCA_API_SECRET_KEY")

    if not grok_api_key:
        logger.error("GROK_API_KEY environment variable not set")
        raise ValueError("Please set the GROK_API_KEY environment variable")

    if not alpaca_api_key:
        logger.error("APCA_API_KEY_ID environment variable not set")
        raise ValueError("Please set the APCA_API_KEY_ID environment variable")

    if not alpaca_secret:
        logger.error("APCA_API_SECRET_KEY environment variable not set")
        raise ValueError("Please set the APCA_API_SECRET_KEY environment variable")

    trading_client = TradingDataClient(alpaca_api_key, alpaca_secret)
    grok_client = GrokAPIClient(api_key=grok_api_key, tradingClient=trading_client)
    stock_client = StockDataClient(alpaca_api_key, alpaca_secret, send_message, grok_client)
    set_stock_client(stock_client)

    await stock_client.run_stream(alpaca_api_key, alpaca_secret)

    asyncio.create_task(stock_client.handleStream())

    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
