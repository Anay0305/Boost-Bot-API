from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from .results import RESULTS
import json

class BoostConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = parse_qs(self.scope["query_string"].decode())
        token = query_string.get("token", [None])[0]

        if not await self.authenticate_token(token):
            await self.close(code=4001)
            return

        await self.channel_layer.group_add("boost", self.channel_name)
        await self.accept()
        print(f"WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("boost", self.channel_name)
        print(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"Received data from {self.channel_name}: {data}")
        RESULTS[data.get('id')] = data

    async def send_data(self, event):
        await self.send(text_data=json.dumps(event["data"]))
        print(f"Query sent to {self.channel_name}: {event['data']}")

    async def authenticate_token(self, token):
        if token == "secrettoken123":
            return True
        return False
