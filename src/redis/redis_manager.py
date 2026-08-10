import redis.asyncio as redis
import logging


logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.redis = None

    async def connect(self):
        self.redis = redis.Redis(
            host=self.host,
            port=self.port,
            decode_responses=False
        )
        if await self.redis.ping():
            logger.info('Проверка связи с redis прошла успешно')
        else:
            logger.warning('WARNING, Redis не отвечает')

    async def get(self, key: str) -> str:
        return await self.redis.get(key)

    async def set(self, key: str, val: str, expire: int = None):
        if expire:
            await self.redis.set(key, val, ex=expire)
        else:
            await self.redis.set(key, val)

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def close(self):
        if self.redis:
            await self.redis.close()
