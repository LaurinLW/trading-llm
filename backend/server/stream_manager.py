import json
import asyncio
import websockets
from typing import Callable, Optional, Awaitable
from server.logger import get_logger

logger = get_logger(__name__)


class StreamManager:
    def __init__(self, send_func: Callable) -> None:
        self.send_func: Callable = send_func
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def ping(self) -> None:
        while True:
            if self.ws and self.ws.state == websockets.State.OPEN:
                await self.ws.ping()
            await asyncio.sleep(30)

    async def run_stream(self, api_key: str, secret_key: str, symbols: list[str]) -> None:
        data = {"action": "auth", "key": api_key, "secret": secret_key}
        self.ws = await websockets.connect("wss://stream.data.alpaca.markets/v2/iex")
        asyncio.create_task(self.ping())
        await self.ws.send(json.dumps(data))
        result = await self.ws.recv()
        logger.info(result)
        result = await self.ws.recv()
        logger.info(result)

        await self.ws.send(json.dumps({"action": "subscribe", "bars": symbols}))
        result = await self.ws.recv()
        logger.info(result)

    async def receive_data(self) -> dict:
        result = await self.ws.recv()
        parsed_result = json.loads(result)
        data = parsed_result[0]
        return data

    async def start_streaming(self, data_handler: Callable[[dict], Awaitable[None]]) -> None:
        while True:
            data = await self.receive_data()
            await data_handler(data)