"""
Redis Client
Für Room-States, Pub/Sub, Session-Storage
"""
from typing import Optional, Dict, Any
import json
from redis import asyncio as aioredis
from app.config import get_settings

settings = get_settings()


class RedisClient:
    """Redis Client Wrapper"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Verbindet mit Redis"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await self.redis.ping()
        print("✅ Redis verbunden")

    async def disconnect(self):
        """Trennt Verbindung"""
        if self.redis:
            await self.redis.close()

    async def set_room_state(self, room_code: str, state: Dict[str, Any], ttl: int = 3600):
        """Speichert Room-Status in Redis"""
        if self.redis:
            key = f"room:{room_code}"
            await self.redis.setex(key, ttl, json.dumps(state))

    async def get_room_state(self, room_code: str) -> Optional[Dict[str, Any]]:
        """Lädt Room-Status aus Redis"""
        if self.redis:
            key = f"room:{room_code}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None

    async def delete_room_state(self, room_code: str):
        """Löscht Room-Status"""
        if self.redis:
            key = f"room:{room_code}"
            await self.redis.delete(key)

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Speichert einen generischen Wert"""
        if self.redis:
            await self.redis.setex(key, ttl, json.dumps(value))

    async def get(self, key: str) -> Optional[Any]:
        """Lädt einen generischen Wert"""
        if self.redis:
            data = await self.redis.get(key)
            return json.loads(data) if data else None

    async def delete(self, key: str):
        """Löscht einen generischen Wert"""
        if self.redis:
            await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Prüft ob Key existiert"""
        if self.redis:
            return await self.redis.exists(key) > 0
        return False

    async def set_refresh_token(self, token: str, user_id: int, ttl: int = 2592000):
        """Speichert Refresh Token in Redis"""
        if self.redis:
            key = f"refresh_token:{user_id}"
            await self.redis.setex(key, ttl, token)

    async def delete_refresh_token(self, user_id: int):
        """Löscht Refresh Token"""
        if self.redis:
            key = f"refresh_token:{user_id}"
            await self.redis.delete(key)

    async def verify_refresh_token(self, token: str) -> Optional[int]:
        """Verifiziert und gibt User-ID zurück"""
        if self.redis:
            # Token als Key suchen
            keys = await self.redis.keys("refresh_token:*")
            for key in keys:
                stored_token = await self.redis.get(key)
                if stored_token == token:
                    return int(key.split(":")[1])
        return None

    async def pubsub_publish(self, channel: str, message: Dict[str, Any]):
        """Sendet eine Nachricht über Pub/Sub"""
        if self.redis:
            await self.redis.publish(channel, json.dumps(message))

    async def pubsub_subscribe(self, channel: str):
        """Abonniert einen Channel"""
        if self.redis:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            return pubsub

    async def pubsub_listen(self, pubsub):
        """Hört auf einen Pub/Sub Channel"""
        if self.redis:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])

    async def cleanup_expired_rooms(self):
        """Reinigt abgelaufene Räume (optional)"""
        if self.redis:
            keys = await self.redis.keys("room:*")
            for key in keys:
                # TTL prüfen
                ttl = await self.redis.ttl(key)
                if ttl == -1:  # Kein TTL gesetzt
                    await self.redis.delete(key)


# Singleton Instance
redis_client = RedisClient()
