import json
from flask import Flask
from flask_cors import CORS

from grokClient import GrokAPIClient
from stockClient import StockDataClient


def create_app(stockClient: StockDataClient, grokClient: GrokAPIClient):
    app = Flask(__name__)
    CORS(app, resources={r"/stockData": {"origins": "http://localhost:5173"}})

    lastData = []
    lastTimeStamp = None

    @app.route("/stockData", methods=["GET"])
    def stockData():
        data = []
        timestamp = None
        while data == []:
            data, timestamp = stockClient.fetch_minute_data("TSLA")

        result = grokClient.getSignal(json.dumps(data, separators=(",", ":")))
        for i, item in enumerate(data):
            item["buySignal"] = i == len(data) - 1 and result == "BUY"
            item["sellSignal"] = i == len(data) - 1 and result == "SELL"
        lastData = data
        lastTimeStamp = timestamp
        return data, 200

    return app
