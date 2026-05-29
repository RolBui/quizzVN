import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RealtimeBroker:
    def __init__(self) -> None:
        self.channel = settings.CHAT_EVENTS_CHANNEL
        self.redis = None
        if not settings.REDIS_URL:
            return
        if not settings.REDIS_URL.startswith(("redis://", "rediss://", "unix://")):
            logger.warning("Invalid REDIS_URL scheme; realtime broker is disabled.")
            return
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    @property
    def is_enabled(self) -> bool:
        return self.redis is not None

    async def publish(self, payload: dict) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.publish(self.channel, json.dumps(payload, default=str))
            return True
        except Exception:
            logger.exception("Failed to publish realtime event to Redis.")
            return False

    async def listen(self, on_event: Callable[[dict], Awaitable[None]]) -> None:
        if not self.redis:
            logger.info("REDIS_URL is not configured; realtime broker listener is disabled.")
            return

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = json.loads(message["data"])
            await on_event(payload)


broker = RealtimeBroker()
