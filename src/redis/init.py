from src.redis.redis_manager import RedisIncidentManager
from src.config import settings

redis_host = settings.REDIS_HOST if settings.MODE == "LOCAL" else settings.REDIS_HOST_DOCKER
redis_manager = RedisIncidentManager(
    host=redis_host,
    port=settings.REDIS_PORT,
)
redis_manager.connect()
