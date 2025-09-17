import json
import logging
import asyncio
from server.grokClient import GrokAPIClient
from typing import TypedDict, List, Tuple
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed
from datetime import datetime, timedelta
import websockets

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
    fivePeriodMovingAverage: float
    tenPeriodMovingAverage: float
    sixPeriodRSI: float


class StockDataClient:
    def __init__(self, api_key: str, secret_key: str, send_func, grokClient: GrokAPIClient, interval: int):
        self.send_func = send_func
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        self.grokClient = grokClient
        self.data = []
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

    def fetch_data(self, symbol: str, now: datetime) -> List[FinancialDataPoint]:

        request_params = StockBarsRequest(feed=DataFeed("iex"), symbol_or_symbols=[symbol], timeframe=TimeFrame(self.interval, TimeFrameUnit("Min")), start=now - timedelta(days=4), end=now)
        symbol_quotes = self.stock_client.get_stock_bars(request_params)

        data = symbol_quotes.data.get(symbol, [])

        processed_data: list[FinancialDataPoint] = [
            FinancialDataPoint(close=entry.close, high=entry.high, low=entry.low, open=entry.open, timestamp=entry.timestamp.isoformat(), trade_count=entry.trade_count, volume=entry.volume) for entry in data
        ]

        for i in range(len(processed_data)):
            processed_data[i]["fivePeriodMovingAverage"] = self.calculateMovingAverage(processed_data[: i + 1], 5)
            processed_data[i]["tenPeriodMovingAverage"] = self.calculateMovingAverage(processed_data[: i + 1], 10)
            processed_data[i]["sixPeriodRSI"] = self.calculateRelativeStrengthIndex(processed_data[: i + 1], 6)

        return processed_data

    def calculateMovingAverage(self, data, periods):
        if len(data) >= periods:
            relevantData = data[-int(periods) :]
            sumOfData = sum([dataPoint["close"] for dataPoint in relevantData])
            return sumOfData / periods
        return data[-1]["close"]

    def calculateRelativeStrengthIndex(self, data, minutes):
        relevantData = data[-int(minutes) :]
        win = []
        loss = []
        for i in range(len(relevantData)):
            if i > 0:
                if relevantData[i - 1]["close"] <= relevantData[i]["close"]:
                    win.append(relevantData[i]["close"] - relevantData[i - 1]["close"])
                else:
                    loss.append(relevantData[i - 1]["close"] - relevantData[i]["close"])

        win = sum(win) / minutes
        loss = sum(loss) / minutes

        if loss > 0:
            rs = win / loss
            return 100 - (100 / (1 + rs))
        return 100

    def getCurrentData(self):
        return self.data

    def getSettings(self):
        return {**self.grokClient.getSettings(), "interval": self.interval, "paper": True }

    async def handleStream(self):
        self.data = self.fetch_data("TSLA", datetime.now())

        while True:
            if len(self.data) > 60:
                self.data = self.data[-60:]

            result = await self.ws.recv()

            parsedResult = json.loads(result)
            data = parsedResult[0]
            dataPoint = FinancialDataPoint(close=data["c"], high=data["h"], low=data["l"], open=data["o"], timestamp=data["t"], trade_count=data["n"], volume=data["v"])
            print(f'Recieved data from websocket (timestamp: {dataPoint["timestamp"]})')
            if datetime.fromisoformat(dataPoint["timestamp"]).minute % self.interval == 0:
                print("This timestamp will be added to the data")
                lastNineMinutes = self.data[-9:]
                lastNineMinutes.append(dataPoint)
                dataPoint["fivePeriodMovingAverage"] = self.calculateMovingAverage(lastNineMinutes, 5)
                dataPoint["tenPeriodMovingAverage"] = self.calculateMovingAverage(lastNineMinutes, 10)
                dataPoint["sixPeriodRSI"] = self.calculateRelativeStrengthIndex(lastNineMinutes, 6)

                shortList = self.data[-15:]
                shortList.append(dataPoint)
                print("Lets run grok")
                signal = self.grokClient.getSignal(shortList, self.interval)

                self.data.append(dataPoint)
                await self.send_func(self.data)
