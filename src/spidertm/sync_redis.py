import logging
import redis

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        # Создаем пул соединений — он поток-безопасный и не пересоздает сокеты понапрасну
        self.pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )

    @property
    def client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)

    def hget(self, name: str, key: str) -> str | None:
        r = self.client
        return r.hget(name, key)

    def hset(self, name: str, key: str, val: str):
        r = self.client
        r.hset(name, key, val)


redis_manager = RedisManager()