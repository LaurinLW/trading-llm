import logging
from typing import TypedDict, List, Tuple
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.live import StockDataStream
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FinancialDataPoint(TypedDict):
    close: float
    high: float
    low: float
    open: float
    timestamp: str
    trade_count: int
    volume: float
    buySignal: bool
    sellSignal: bool


async def quote_data_handler(data):
    print(data)


def randomDateTime():
    start_date = datetime.now() - timedelta(days=2 * 365)

    random_days = random.randint(0, 2 * 365)
    random_hour = random.randint(10, 18)
    random_minute = random.randint(0, 59)
    return start_date + timedelta(days=random_days, hours=random_hour - start_date.hour, minutes=random_minute - start_date.minute)


class StockDataClient:
    def __init__(self, api_key: str, secret_key: str, mode: str):
        self.mode = mode
        if mode == "Historic":
            self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        else:
            self.stock_client = StockDataStream(api_key, secret_key)
            self.stock_client.subscribe_quotes(quote_data_handler, "TSLA")
            self.stock_client.run()
        logger.info("StockDataClient initialized")

    def fetch_minute_data(self, symbol: str, time=None) -> Tuple[List[FinancialDataPoint], datetime]:
        startTime = time
        if not startTime:
            startTime = randomDateTime()

        request_params = StockBarsRequest(feed="iex", symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute, start=startTime, end=startTime + timedelta(minutes=10))
        symbol_quotes = self.stock_client.get_stock_bars(request_params)

        data = symbol_quotes.data.get(symbol, [])

        processed_data: list[FinancialDataPoint] = [
            FinancialDataPoint(close=entry.close, high=entry.high, low=entry.low, open=entry.open, timestamp=entry.timestamp.isoformat(), trade_count=entry.trade_count, volume=entry.volume, sellSignal=False, buySignal=False)
            for entry in data
        ]
        return processed_data, startTime
