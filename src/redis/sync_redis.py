import logging
import redis
from src.config import settings

logger = logging.getLogger(__name__)

import datetime


class RedisIncidentManager:
    def __init__(self, url: str):
        self.pool = redis.ConnectionPool.from_url(
            url,
            decode_responses=True
        )
        self.client = redis.Redis(connection_pool=self.pool)

    def _get_daily_key(self, base_name: str, date: datetime.date | None = None) -> str:
        """Формирует ключ с датой, например: siem:processed_incidents:2026-09-16"""
        target_date = date or datetime.date.today()
        return f"{base_name}:{target_date.isoformat()}"

    def get_incident_etime(self, base_name: str, inc_hash: str) -> str | None:
        """Ищет время события за сегодня и за вчера."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        # Сначала смотрим за сегодня
        val = self.client.hget(self._get_daily_key(base_name, today), inc_hash)
        if val is not None:
            return val

        # Если нет за сегодня, проверяем вчерашний день
        return self.client.hget(self._get_daily_key(base_name, yesterday), inc_hash)

    def save_incident(self, base_name: str, inc_hash: str, etime: str, ttl_days: int = 7):
        """Сохраняет инцидент в ключ текущего дня и продлевает TTL ключа."""
        daily_key = self._get_daily_key(base_name)

        # HSET возвращает количество добавленных полей
        self.client.hset(daily_key, inc_hash, etime)

        # Устанавливаем время жизни ключа (например, дней)
        # Redis будет автоматически удалять весь суточный хэш целиком
        self.client.expire(daily_key, ttl_days * 3600)

redis_incident_manager = RedisIncidentManager(settings.REDIS_URL)