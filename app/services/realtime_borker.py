import json
import redis.asyncio as redis

from app.core.config import settings


class RealtimeBroker:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.channel = settings.CHAT_EVENTS_CHANNEL

    async def publish(self, payload: dict):
        await self.redis.publish(self.channel, json.dumps(payload, default=str))

    async def listen(self, on_event):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = json.loads(message["data"])
            await on_event(payload)


broker = RealtimeBroker()