from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from dataclasses import asdict
from datetime import datetime

from config import Config
from server import StockDataClient, TradingDataClient, get_logger

logger = get_logger(__name__)

config = Config()

def to_dict(obj):
    d = asdict(obj)
    if 'timestamp' in d and isinstance(d['timestamp'], datetime):
        d['timestamp'] = d['timestamp'].isoformat()
    return d

app = FastAPI()

stock_client = None
trading_client = None
connected = set()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
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
    if isinstance(message, dict):
        message = {k: [to_dict(item) if hasattr(item, '__dataclass_fields__') else item for item in v] if isinstance(v, list) else v for k, v in message.items()}
    message_str = json.dumps(message)
    await asyncio.gather(*(ws.send_text(message_str) for ws in connected), return_exceptions=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    connected.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        logger.info(f"Client disconnected: {e}")
    finally:
        connected.remove(websocket)
        logger.info("WebSocket connection closed")


@app.get("/data")
async def get_data():
    if stock_client:
        data = await stock_client.get_current_data()
        return JSONResponse(content={k: [to_dict(item) for item in v] for k, v in data.items()})
    return JSONResponse(content={"error": "No stock client available"})


@app.get("/positions")
async def get_positions():
    if trading_client:
        data = trading_client.get_open_positions()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No trading client available"})


@app.get("/account")
async def get_account_info():
    if trading_client:
        data = trading_client.get_account_info()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No trading client available"})


@app.get("/portfoliovalue")
async def get_portfolio_value():
    if trading_client:
        one, fifteen, hour, day = trading_client.get_account_value()
        return JSONResponse(content={"one": one, "fifteen": fifteen, "hour": hour, "day": day})
    return JSONResponse(content={"error": "No trading client available"})


@app.get("/settings")
async def get_settings():
    if stock_client:
        data = stock_client.get_settings()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No stock client available"})
