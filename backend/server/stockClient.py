import json
import asyncio
import threading
from dataclasses import asdict
from server.grokClient import GrokAPIClient
from server.data_processor import DataProcessor
from server.models import FinancialDataPoint
from server.stream_manager import StreamManager
from server.logger import get_logger
from typing import List, Tuple, Dict, Callable, Any

from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed
from datetime import datetime, timedelta

logger = get_logger(__name__)


def serialize_financial_data_point(obj: FinancialDataPoint) -> dict:
    d = asdict(obj)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


class StockDataClient:
    def __init__(self, api_key: str, secret_key: str, send_func: Callable, grok_client: GrokAPIClient, interval: int) -> None:
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("interval must be a positive integer")
        self.api_key = api_key
        self.secret_key = secret_key
        self.send_func: Callable = send_func
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        self.grok_client: GrokAPIClient = grok_client
        self.data_1min: List[FinancialDataPoint] = []
        self.data_15min: List[FinancialDataPoint] = []
        self.data_1hour: List[FinancialDataPoint] = []
        self.data_1day: List[FinancialDataPoint] = []
        self.interval: int = interval
        self.data_lock = asyncio.Lock()
        self.processor = DataProcessor()
        self.stream_manager = StreamManager(send_func)
        logger.info("StockDataClient initialized")

    def calculate_kpi(self, data_point: FinancialDataPoint, data) -> FinancialDataPoint:
        last_nine_intervals = data[-9:]
        data_point.fivePeriodMovingAverage = self.processor.calculate_moving_average(last_nine_intervals, 5)
        data_point.tenPeriodMovingAverage = self.processor.calculate_moving_average(last_nine_intervals, 10)
        data_point.sixPeriodRsi = self.processor.calculate_relative_strength_index(last_nine_intervals, 6)
        return data_point

    async def quote_data_handler(self, data: dict) -> None:
        data_point = FinancialDataPoint(
            close=data["c"],
            high=data["h"],
            low=data["l"],
            open=data["o"],
            timestamp=datetime.fromisoformat(data["t"]),
            tradeCount=int(data.get("n", 0)),
            volume=data["v"],
        )

        async with self.data_lock:
            if len(self.data_1min) > 60:
                self.data_1min = self.data_1min[-60:]
            if len(self.data_15min) > 60:
                self.data_15min = self.data_15min[-60:]
            if len(self.data_1hour) > 60:
                self.data_1hour = self.data_1hour[-60:]
            if len(self.data_1day) > 60:
                self.data_1day = self.data_1day[-60:]

            if not self.data_1min or (data_point.timestamp - self.data_1min[-1].timestamp).total_seconds() / 60 >= 1:
                self.data_1min.append(self.calculate_kpi(data_point, self.data_1min))

            if not self.data_15min or (data_point.timestamp - self.data_15min[-1].timestamp).total_seconds() / 60 >= 15:
                self.data_15min.append(self.calculate_kpi(data_point, self.data_15min))

            if not self.data_1hour or (data_point.timestamp - self.data_1hour[-1].timestamp).total_seconds() / 60 >= 60:
                self.data_1hour.append(self.calculate_kpi(data_point, self.data_1hour))

            if not self.data_1day or (data_point.timestamp - self.data_1day[-1].timestamp).total_seconds() / 60 >= 60 * 24:
                self.data_1day.append(self.calculate_kpi(data_point, self.data_1day))

        logger.info(f"Received data from websocket (timestamp: {data_point.timestamp})")
        if data_point.timestamp.minute % self.interval == 0:
            logger.info("This timestamp will be added to the data")
            short_list = self.fetch_data("TSLA", datetime.now(), self.interval)[-15:]
            short_list.append(self.calculate_kpi(data_point, short_list))

            grok_thread = threading.Thread(target=self.run_grok_in_thread, args=(short_list, self.interval))
            grok_thread.daemon = True
            grok_thread.start()

        await self.send_func({"one": self.data_1min, "fifteen": self.data_15min, "hour": self.data_1hour, "day": self.data_1day})

    def fetch_data(self, symbol: str, now: datetime, interval: int) -> List[FinancialDataPoint]:
        timeframe = None
        if interval < 60:
            timeframe = TimeFrame(interval, TimeFrameUnit("Min"))
        elif interval == 60:
            timeframe = TimeFrame(1, TimeFrameUnit("Hour"))
        else:
            timeframe = TimeFrame(1, TimeFrameUnit("Day"))
        request_params = StockBarsRequest(
            feed=DataFeed("iex"), symbol_or_symbols=[symbol], timeframe=timeframe, start=now - timedelta(days=10), end=now
        )
        symbol_quotes = self.stock_client.get_stock_bars(request_params)

        data = symbol_quotes.data.get(symbol, [])

        processed_data: list[FinancialDataPoint] = [
            FinancialDataPoint(
                close=entry.close,
                high=entry.high,
                low=entry.low,
                open=entry.open,
                timestamp=entry.timestamp,
                tradeCount=int(entry.trade_count or 0),
                volume=entry.volume,
            )
            for entry in data
        ]

        for i in range(len(processed_data)):
            processed_data[i].fivePeriodMovingAverage = self.processor.calculate_moving_average(processed_data[: i + 1], 5)
            processed_data[i].tenPeriodMovingAverage = self.processor.calculate_moving_average(processed_data[: i + 1], 10)
            processed_data[i].sixPeriodRsi = self.processor.calculate_relative_strength_index(processed_data[: i + 1], 6)

        return processed_data

    async def get_current_data(self) -> Dict[str, List[FinancialDataPoint]]:
        async with self.data_lock:
            return {
                "one": self.data_1min[-60:],
                "fifteen": self.data_15min[-60:],
                "hour": self.data_1hour[-60:],
                "day": self.data_1day[-60:],
            }

    def get_settings(self) -> Dict[str, Any]:
        return {**self.grok_client.get_settings(), "interval": self.interval, "paper": True}

    def run_grok_in_thread(self, short_list: List[FinancialDataPoint], interval: int) -> None:
        try:
            stock_data_str = json.dumps([serialize_financial_data_point(item) for item in short_list])
            signal = self.grok_client.get_signal(stock_data_str, interval)
            logger.info(f"Grok signal processed in thread: {signal}")
        except Exception as e:
            logger.error(f"Error in grok thread: {e}")

    async def start_streaming(self) -> None:
        async with self.data_lock:
            self.data_1min = self.fetch_data("TSLA", datetime.now(), 1)
            self.data_15min = self.fetch_data("TSLA", datetime.now(), 15)
            self.data_1hour = self.fetch_data("TSLA", datetime.now(), 60)
            self.data_1day = self.fetch_data("TSLA", datetime.now(), 60 * 24)

        await self.stream_manager.run_stream(self.api_key, self.secret_key, ["TSLA"])
        asyncio.create_task(self.stream_manager.start_streaming(self.quote_data_handler))
