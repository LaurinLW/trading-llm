from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import asyncio

app = FastAPI()

stock_client = None
connected = set()


def set_stock_client(client):
    global stock_client
    stock_client = client


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


@app.get("/settings")
async def get_settings():
    if stock_client:
        data = stock_client.getSettings()
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "No stock client available"})
