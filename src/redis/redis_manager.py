import datetime
import hashlib
import json
import logging
import redis

logger = logging.getLogger(__name__)


class RedisIncidentManager:
    CORRELATION_PREFIX = "siem:correlation"

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.client: redis.Redis | None = None

    def connect(self):
        """Инициализация подключения к Redis."""
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            decode_responses=True
        )
        try:
            if self.client.ping():
                logger.info('Проверка связи с Redis прошла успешно')
        except redis.ConnectionError:
            logger.error('Ошибка подключения к Redis')

    def close(self):
        """Закрытие соединения."""
        if self.client:
            self.client.close()

    # ==========================================================
    # BASIC OPERATIONS
    # ==========================================================

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, val: str, expire: int | None = None):
        self.client.set(key, val, ex=expire)

    def delete(self, key: str):
        self.client.delete(key)

    # ==========================================================
    # INCIDENTS
    # ==========================================================

    @staticmethod
    def _get_daily_key(base_name: str) -> str:
        target_date = datetime.date.today()
        return f"{base_name}:{target_date.isoformat()}"

    def get_incident_etime(self, base_name: str, inc_hash: str) -> str | None:
        return self.client.hget(
            self._get_daily_key(base_name),
            inc_hash
        )

    def save_incident(self, base_name: str, inc_hash: str, etime: str, ttl_days: int = 7):
        daily_key = self._get_daily_key(base_name)

        # Используем pipeline, чтобы выполнилось одной транзакцией в Redis
        pipe = self.client.pipeline()
        pipe.hset(daily_key, inc_hash, etime)
        pipe.expire(daily_key, ttl_days * 24 * 3600)
        pipe.execute()

    # ==========================================================
    # CORRELATION GROUPS
    # ==========================================================

    def make_correlation_hash(
            self,
            source_ip: str | None,
            attack: str,
            origin_name: str | None,
    ) -> str:
        raw = "|".join([
            source_ip or "",
            attack or "",
            origin_name or "",
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_correlation_key(self, correlation_hash: str) -> str:
        return f"{self.CORRELATION_PREFIX}:{correlation_hash}"

    def get_correlation_group(self, correlation_hash: str) -> dict | None:
        key = self.get_correlation_key(correlation_hash)
        value = self.client.get(key)

        if value is None:
            return None

        return json.loads(value)

    def create_correlation_group(
            self,
            correlation_hash: str,
            group: dict,
            ttl: int = 30,
    ) -> bool:
        key = self.get_correlation_key(correlation_hash)

        # nx=True: создать только если ключ НЕ существует
        created = self.client.set(
            key,
            json.dumps(group, ensure_ascii=False),
            ex=ttl,
            nx=True,
        )
        return bool(created)

    def save_correlation_group(
            self,
            correlation_hash: str,
            group: dict,
            ttl: int = 30,
    ):
        key = self.get_correlation_key(correlation_hash)
        self.client.set(
            key,
            json.dumps(group, ensure_ascii=False),
            ex=ttl,
        )

    def delete_correlation_group(self, correlation_hash: str):
        key = self.get_correlation_key(correlation_hash)
        self.client.delete(key)

    def correlation_exists(self, correlation_hash: str) -> bool:
        key = self.get_correlation_key(correlation_hash)
        return bool(self.client.exists(key))