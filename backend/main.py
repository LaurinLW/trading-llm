import asyncio
import uvicorn
from dotenv import load_dotenv
from config import Config
from server import GrokAPIClient, StockDataClient, TradingDataClient, get_logger
from app import app, set_stock_client, send_message, set_trading_client

logger = get_logger(__name__)


async def main():
    load_dotenv()

    config = Config()

    trading_client = TradingDataClient(config.alpaca_api_key, config.alpaca_secret)
    grok_client = GrokAPIClient(api_key=config.grok_api_key, tradingClient=trading_client, disable=config.disable_grok)
    stock_client = StockDataClient(config.alpaca_api_key, config.alpaca_secret, send_message, grok_client, config.interval)
    set_stock_client(stock_client)
    set_trading_client(trading_client)

    await stock_client.run_stream(config.alpaca_api_key, config.alpaca_secret)

    asyncio.create_task(stock_client.handleStream())

    server_config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(server_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
