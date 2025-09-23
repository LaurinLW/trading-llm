import json
import logging
import asyncio
import threading
from server.grokClient import GrokAPIClient
from typing import List, Tuple
from dataclasses import dataclass
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed
from datetime import datetime, timedelta
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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
    def __init__(self, api_key: str, secret_key: str, send_func, grokClient: GrokAPIClient, interval: int):
        self.send_func = send_func
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        self.grokClient = grokClient
        self.dataOne = []
        self.dataFifteen = []
        self.dataHour = []
        self.dataDay = []
        self.interval = interval
        logger.info("StockDataClient initialized")

    async def quote_data_handler(self, data):
        await self.send_func(data)

    async def ping(self):
        while True:
            if self.ws and self.ws.state == websockets.State.OPEN:
                await self.ws.ping()
            await asyncio.sleep(30)

    async def run_stream(self, api_key: str, secret_key: str):
        data = {"action": "auth", "key": api_key, "secret": secret_key}
        self.ws = await websockets.connect("wss://stream.data.alpaca.markets/v2/iex")
        asyncio.create_task(self.ping())
        await self.ws.send(json.dumps(data))
        result = await self.ws.recv()
        print(result)
        result = await self.ws.recv()
        print(result)

        await self.ws.send(json.dumps({"action": "subscribe", "bars": ["TSLA"]}))
        result = await self.ws.recv()
        print(result)

    def fetch_data(self, symbol: str, now: datetime, interval) -> List[FinancialDataPoint]:
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

    def calculateMovingAverage(self, data, periods):
        if len(data) >= periods:
            relevantData = data[-int(periods) :]
            sumOfData = sum([dataPoint.close for dataPoint in relevantData])
            return sumOfData / periods
        return data[-1].close

    def calculateRelativeStrengthIndex(self, data, minutes):
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

    def getCurrentData(self):
        return {"one": self.dataOne[-60:], "fifteen": self.dataFifteen[-60:], "hour": self.dataHour[-60:], "day": self.dataDay[-60:]}

    def getSettings(self):
        return {**self.grokClient.getSettings(), "interval": self.interval, "paper": True}

    def run_grok_in_thread(self, shortList, interval):
        try:
            signal = self.grokClient.getSignal(shortList, interval)
            logger.info(f"Grok signal processed in thread: {signal}")
        except Exception as e:
            logger.error(f"Error in grok thread: {e}")

    async def handleStream(self):
        self.dataOne = self.fetch_data("TSLA", datetime.now(), 1)
        self.dataFifteen = self.fetch_data("TSLA", datetime.now(), 15)
        self.dataHour = self.fetch_data("TSLA", datetime.now(), 60)
        self.dataDay = self.fetch_data("TSLA", datetime.now(), 60 * 24)

        while True:
            if len(self.dataOne) > 60:
                self.dataOne = self.dataOne[-60:]
            if len(self.dataFifteen) > 60:
                self.dataFifteen = self.dataFifteen[-60:]
            if len(self.dataHour) > 60:
                self.dataHour = self.dataHour[-60:]
            if len(self.dataDay) > 60:
                self.dataDay = self.dataDay[-60:]

            result = await self.ws.recv()

            parsedResult = json.loads(result)
            data = parsedResult[0]
            dataPoint = FinancialDataPoint(close=data["c"], high=data["h"], low=data["l"], open=data["o"], timestamp=datetime.fromisoformat(data["t"]), trade_count=int(data["n"] or 0), volume=data["v"])

            if (dataPoint.timestamp - self.dataOne[-1].timestamp).total_seconds() / 60 >= 1:
                self.dataOne.append(dataPoint)

            if (dataPoint.timestamp - self.dataFifteen[-1].timestamp).total_seconds() / 60 >= 15:
                self.dataFifteen.append(dataPoint)

            if (dataPoint.timestamp - self.dataHour[-1].timestamp).total_seconds() / 60 >= 60:
                self.dataHour.append(dataPoint)

            if (dataPoint.timestamp - self.dataDay[-1].timestamp).total_seconds() / 60 >= 60 * 24:
                self.dataDay.append(dataPoint)

            print(f"Recieved data from websocket (timestamp: {dataPoint.timestamp})")
            if dataPoint.timestamp.minute % self.interval == 0:
                print("This timestamp will be added to the data")
                shortList = self.fetch_data("TSLA", datetime.now(), self.interval)
                lastNineIntervals = shortList[-9:]
                lastNineIntervals.append(dataPoint)
                dataPoint.fivePeriodMovingAverage = self.calculateMovingAverage(lastNineIntervals, 5)
                dataPoint.tenPeriodMovingAverage = self.calculateMovingAverage(lastNineIntervals, 10)
                dataPoint.sixPeriodRSI = self.calculateRelativeStrengthIndex(lastNineIntervals, 6)

                grok_thread = threading.Thread(target=self.run_grok_in_thread, args=(shortList, self.interval))
                grok_thread.daemon = True
                grok_thread.start()

            await self.send_func({"one": self.dataOne, "fifteen": self.dataFifteen, "hour": self.dataHour, "day": self.dataDay})
