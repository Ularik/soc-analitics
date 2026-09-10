import logging
import redis
from src.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self, url: str):
        # Создаем пул соединений прямо из URL вида "redis://localhost:6379/0"
        self.pool = redis.ConnectionPool.from_url(
            url,
            decode_responses=True
        )

    @property
    def client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)

    def hget(self, name: str, key: str) -> str | None:
        return self.client.hget(name, key)

    def hset(self, name: str, key: str, val: str):
        self.client.hset(name, key, val)


# Передаем полностью сформированный URL (например, "redis://redis:6379/0")
redis_manager = RedisManager(url=settings.REDIS_URL)