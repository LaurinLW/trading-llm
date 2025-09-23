import json
import asyncio
import threading
from server.grokClient import GrokAPIClient
from server.logger import get_logger
from typing import List, Tuple, Dict, Callable, Any
from dataclasses import dataclass
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed
from datetime import datetime, timedelta
import websockets

logger = get_logger(__name__)


@dataclass
class FinancialDataPoint:
    close: float
    high: float
    low: float
    open: float
    timestamp: datetime
    trade_count: int
    volume: float
    fivePeriodMovingAverage: float = 0.0
    tenPeriodMovingAverage: float = 0.0
    sixPeriodRSI: float = 0.0


class StockDataClient:
    def __init__(self, api_key: str, secret_key: str, send_func: Callable, grokClient: GrokAPIClient, interval: int) -> None:
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("interval must be a positive integer")
        self.send_func: Callable = send_func
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        self.grokClient: GrokAPIClient = grokClient
        self.data_1min: List[FinancialDataPoint] = []
        self.data_15min: List[FinancialDataPoint] = []
        self.data_1hour: List[FinancialDataPoint] = []
        self.data_1day: List[FinancialDataPoint] = []
        self.interval: int = interval
        self.data_lock = asyncio.Lock()
        logger.info("StockDataClient initialized")

    async def quote_data_handler(self, data) -> None:
        await self.send_func(data)

    async def ping(self) -> None:
        while True:
            if self.ws and self.ws.state == websockets.State.OPEN:
                await self.ws.ping()
            await asyncio.sleep(30)

    async def run_stream(self, api_key: str, secret_key: str) -> None:
        data = {"action": "auth", "key": api_key, "secret": secret_key}
        self.ws = await websockets.connect("wss://stream.data.alpaca.markets/v2/iex")
        asyncio.create_task(self.ping())
        await self.ws.send(json.dumps(data))
        result = await self.ws.recv()
        logger.info(result)
        result = await self.ws.recv()
        logger.info(result)

        await self.ws.send(json.dumps({"action": "subscribe", "bars": ["TSLA"]}))
        result = await self.ws.recv()
        logger.info(result)

    def fetch_data(self, symbol: str, now: datetime, interval: int) -> List[FinancialDataPoint]:
        timeframe = None
        if interval < 60:
            timeframe = TimeFrame(interval, TimeFrameUnit("Min"))
        elif interval == 60:
            timeframe = TimeFrame(1, TimeFrameUnit("Hour"))
        else:
            timeframe = TimeFrame(1, TimeFrameUnit("Day"))
        request_params = StockBarsRequest(feed=DataFeed("iex"), symbol_or_symbols=[symbol], timeframe=timeframe, start=now - timedelta(days=10), end=now)
        symbol_quotes = self.stock_client.get_stock_bars(request_params)

        data = symbol_quotes.data.get(symbol, [])

        processed_data: list[FinancialDataPoint] = [
            FinancialDataPoint(close=entry.close, high=entry.high, low=entry.low, open=entry.open, timestamp=entry.timestamp, trade_count=int(entry.trade_count or 0), volume=entry.volume) for entry in data
        ]

        for i in range(len(processed_data)):
            processed_data[i].fivePeriodMovingAverage = self.calculateMovingAverage(processed_data[: i + 1], 5)
            processed_data[i].tenPeriodMovingAverage = self.calculateMovingAverage(processed_data[: i + 1], 10)
            processed_data[i].sixPeriodRSI = self.calculateRelativeStrengthIndex(processed_data[: i + 1], 6)

        return processed_data

    def calculateMovingAverage(self, data: List[FinancialDataPoint], periods: int) -> float:
        if len(data) >= periods:
            relevantData = data[-int(periods) :]
            sumOfData = sum([dataPoint.close for dataPoint in relevantData])
            return sumOfData / periods
        return data[-1].close

    def calculateRelativeStrengthIndex(self, data: List[FinancialDataPoint], minutes: int) -> float:
        relevantData = data[-int(minutes) :]
        win = []
        loss = []
        for i in range(len(relevantData)):
            if i > 0:
                if relevantData[i - 1].close <= relevantData[i].close:
                    win.append(relevantData[i].close - relevantData[i - 1].close)
                else:
                    loss.append(relevantData[i - 1].close - relevantData[i].close)

        win = sum(win) / minutes
        loss = sum(loss) / minutes

        if loss > 0:
            rs = win / loss
            return 100 - (100 / (1 + rs))
        return 100

    async def getCurrentData(self) -> Dict[str, List[FinancialDataPoint]]:
        async with self.data_lock:
            return {"one": self.data_1min[-60:], "fifteen": self.data_15min[-60:], "hour": self.data_1hour[-60:], "day": self.data_1day[-60:]}

    def getSettings(self) -> Dict[str, Any]:
        return {**self.grokClient.getSettings(), "interval": self.interval, "paper": True}

    def run_grok_in_thread(self, shortList: List[FinancialDataPoint], interval: int) -> None:
        try:
            signal = self.grokClient.getSignal(shortList, interval)
            logger.info(f"Grok signal processed in thread: {signal}")
        except Exception as e:
            logger.error(f"Error in grok thread: {e}")

    async def handleStream(self) -> None:
        async with self.data_lock:
            self.data_1min = self.fetch_data("TSLA", datetime.now(), 1)
            self.data_15min = self.fetch_data("TSLA", datetime.now(), 15)
            self.data_1hour = self.fetch_data("TSLA", datetime.now(), 60)
            self.data_1day = self.fetch_data("TSLA", datetime.now(), 60 * 24)

        while True:
            result = await self.ws.recv()

            parsedResult = json.loads(result)
            data = parsedResult[0]
            dataPoint = FinancialDataPoint(close=data["c"], high=data["h"], low=data["l"], open=data["o"], timestamp=datetime.fromisoformat(data["t"]), trade_count=int(data["n"] or 0), volume=data["v"])

            async with self.data_lock:
                if len(self.data_1min) > 60:
                    self.data_1min = self.data_1min[-60:]
                if len(self.data_15min) > 60:
                    self.data_15min = self.data_15min[-60:]
                if len(self.data_1hour) > 60:
                    self.data_1hour = self.data_1hour[-60:]
                if len(self.data_1day) > 60:
                    self.data_1day = self.data_1day[-60:]

                if (dataPoint.timestamp - self.data_1min[-1].timestamp).total_seconds() / 60 >= 1:
                    self.data_1min.append(dataPoint)

                if (dataPoint.timestamp - self.data_15min[-1].timestamp).total_seconds() / 60 >= 15:
                    self.data_15min.append(dataPoint)

                if (dataPoint.timestamp - self.data_1hour[-1].timestamp).total_seconds() / 60 >= 60:
                    self.data_1hour.append(dataPoint)

                if (dataPoint.timestamp - self.data_1day[-1].timestamp).total_seconds() / 60 >= 60 * 24:
                    self.data_1day.append(dataPoint)

            logger.info(f"Received data from websocket (timestamp: {dataPoint.timestamp})")
            if dataPoint.timestamp.minute % self.interval == 0:
                logger.info("This timestamp will be added to the data")
                shortList = self.fetch_data("TSLA", datetime.now(), self.interval)
                lastNineIntervals = shortList[-9:]
                lastNineIntervals.append(dataPoint)
                dataPoint.fivePeriodMovingAverage = self.calculateMovingAverage(lastNineIntervals, 5)
                dataPoint.tenPeriodMovingAverage = self.calculateMovingAverage(lastNineIntervals, 10)
                dataPoint.sixPeriodRSI = self.calculateRelativeStrengthIndex(lastNineIntervals, 6)

                grok_thread = threading.Thread(target=self.run_grok_in_thread, args=(shortList, self.interval))
                grok_thread.daemon = True
                grok_thread.start()

            await self.send_func({"one": self.data_1min, "fifteen": self.data_15min, "hour": self.data_1hour, "day": self.data_1day})
