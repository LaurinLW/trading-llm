import json
import logging
import threading
import time
import asyncio
from server.grokClient import GrokAPIClient
from typing import TypedDict, List, Tuple
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import random
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
    buySignal: bool
    sellSignal: bool
    fiveMinMovingAverage: float
    tenMinMovingAverage: float
    sixMinRSI: float


def randomDateTime():
    start_date = datetime.now() - timedelta(days=2 * 365)

    random_days = random.randint(0, 2 * 365)
    random_hour = random.randint(10, 18)
    random_minute = random.randint(0, 59)
    return start_date + timedelta(days=random_days, hours=random_hour - start_date.hour, minutes=random_minute - start_date.minute)


class StockDataClient:
    def __init__(self, api_key: str, secret_key: str, send_func, grokClient: GrokAPIClient):
        self.send_func = send_func
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        self.grokClient = grokClient
        self.data = []
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

    def fetch_minute_data(self, symbol: str, time=None) -> Tuple[List[FinancialDataPoint], datetime]:
        startTime = time
        if not startTime:
            startTime = randomDateTime()

        request_params = StockBarsRequest(feed="iex", symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute, start=startTime, end=startTime + timedelta(minutes=60))
        symbol_quotes = self.stock_client.get_stock_bars(request_params)

        data = symbol_quotes.data.get(symbol, [])

        processed_data: list[FinancialDataPoint] = [
            FinancialDataPoint(close=entry.close, high=entry.high, low=entry.low, open=entry.open, timestamp=entry.timestamp.isoformat(), trade_count=entry.trade_count, volume=entry.volume, sellSignal=False, buySignal=False)
            for entry in data
        ]

        for i in range(len(processed_data)):
            processed_data[i]["fiveMinMovingAverage"] = self.calculateMovingAverage(processed_data[: i + 1], 5)
            processed_data[i]["tenMinMovingAverage"] = self.calculateMovingAverage(processed_data[: i + 1], 10)
            processed_data[i]["sixMinRSI"] = self.calculateRelativeStrengthIndex(processed_data[: i + 1], 6)

        return processed_data, startTime

    def calculateMovingAverage(self, data, minutes):
        if len(data) >= minutes:
            relevantData = data[-int(minutes) :]
            sumOfData = sum([dataPoint["close"] for dataPoint in relevantData])
            return sumOfData / minutes
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

    async def handleStream(self):
        hours = 0
        now = datetime.now()
        now = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        while self.data == []:
            self.data, _ = self.fetch_minute_data("TSLA", now - timedelta(hours=hours))
            hours = hours + 1

        while True:
            await self.send_func(self.data)
            result = await self.ws.recv()

            parsedResult = json.loads(result)
            data = parsedResult[0]
            dataPoint = FinancialDataPoint(close=data["c"], high=data["h"], low=data["l"], open=data["o"], timestamp=data["t"], trade_count=data["n"], volume=data["v"], sellSignal=False, buySignal=False)

            lastNineMinutes = self.data[-9:]
            lastNineMinutes.append(dataPoint)
            dataPoint["fiveMinMovingAverage"] = self.calculateMovingAverage(lastNineMinutes, 5)
            dataPoint["tenMinMovingAverage"] = self.calculateMovingAverage(lastNineMinutes, 10)
            dataPoint["sixMinRSI"] = self.calculateRelativeStrengthIndex(lastNineMinutes, 6)

            if len(self.data) > 60:
                self.data.pop(0)

            shortList = self.data[-15:]
            shortList.append(dataPoint)
            if datetime.now().hour >= 16:
                signal = self.grokClient.getSignal(shortList)
                if signal:
                    dataPoint["sellSignal"] = signal == "SELL"
                    dataPoint["buySignal"] = signal == "BUY"

            self.data.append(dataPoint)
