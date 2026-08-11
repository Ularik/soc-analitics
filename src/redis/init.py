from src.redis.redis_manager import RedisManager
from src.config import settings

redis_host = settings.REDIS_HOST if settings.MODE == "LOCAL" else settings.REDIS_HOST_DOCKER
redis_manager = RedisManager(
    host=redis_host,
    port=settings.REDIS_PORT,
)
