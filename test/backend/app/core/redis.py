import redis.asyncio as aioredis

from app.core.config import settings


class RedisClient:
    def __init__(self):
        self._redis = None

    async def initialize(self):
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self):
        if self._redis:
            await self._redis.close()

    @property
    def client(self):
        return self._redis

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        await self._redis.set(key, value, ex=ex)

    async def delete(self, *keys: str):
        if keys:
            await self._redis.delete(*keys)

    async def delete_pattern(self, pattern: str) -> None:
        keys = [key async for key in self._redis.scan_iter(match=pattern)]
        if keys:
            await self.delete(*keys)

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(key)


redis_client = RedisClient()
