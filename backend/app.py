from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from server import StockDataClient
from server import TradingDataClient

app = FastAPI()

stock_client = None
trading_client = None
connected = set()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def set_stock_client(client: StockDataClient):
    global stock_client
    stock_client = client


def set_trading_client(client: TradingDataClient):
    global trading_client
    trading_client = client


async def send_message(message):
    message_str = str(message).replace("'", '"').replace("False", "false").replace("True", "true")
    await asyncio.gather(*(ws.send_text(message_str) for ws in connected), return_exceptions=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established")
    connected.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f"Client disconnected: {e}")
    finally:
        connected.remove(websocket)
        print("WebSocket connection closed")


@app.get("/data")
async def get_data():
    if stock_client:
        data = stock_client.getCurrentData()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No stock client available"})


@app.get("/positions")
async def get_open_position():
    if trading_client:
        data = trading_client.getOpenPositions()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No trading client available"})


@app.get("/account")
async def get_account():
    if trading_client:
        data = trading_client.getAccountInfo()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No trading client available"})


@app.get("/portfoliovalue")
async def get_portfolio():
    if trading_client:
        one, fifteen, hour, day = trading_client.getAccountValue()
        return JSONResponse(content={"one": one, "fifteen": fifteen, "hour": hour, "day": day})
    return JSONResponse(content={"error": "No trading client available"})


@app.get("/settings")
async def get_settings():
    if stock_client:
        data = stock_client.getSettings()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No stock client available"})
