import asyncio
import websockets

class Gateway:
    def __init__(self):
        self.connected = set()

    async def echo(self, websocket):
        print("WebSocket connection established")
        try:
            self.connected.add(websocket)
            async for _ in websocket:
                pass
        except Exception as e:
            print(f"Client disconnected: {e}")
        finally:
            self.connected.remove(websocket)
            print("WebSocket connection closed")

    async def sendMessage(self, message):
        messageStr = str(message).replace('\'', '\"').replace('False', 'false').replace('True', 'true')
        await asyncio.gather(*(ws.send(messageStr) for ws in self.connected), return_exceptions=True)
    
    async def startGateway(self):
        async with websockets.serve(self.echo, "0.0.0.0", 8765):
            print("WebSocket server started on ws://0.0.0.0:8765")
            await asyncio.Future()
    
    def run_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.startGateway())