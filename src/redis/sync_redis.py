import logging
import datetime
import hashlib
import json

import redis

from src.config import settings

logger = logging.getLogger(__name__)

class RedisIncidentManager:

    def __init__(self, url: str):
        self.pool = redis.ConnectionPool.from_url(
            url,
            decode_responses=True
        )
        self.client = redis.Redis(connection_pool=self.pool)

    # ==========================================================
    # DAILY INCIDENTS
    # ==========================================================

    def _get_daily_key(
        self,
        base_name: str,
        date: datetime.date | None = None
    ) -> str:
        target_date = date or datetime.date.today()
        return f"{base_name}:{target_date.isoformat()}"

    def get_incident_etime(
        self,
        base_name: str,
        inc_hash: str
    ) -> str | None:

        today = datetime.date.today()

        val = self.client.hget(
            self._get_daily_key(base_name, today),
            inc_hash
        )

        return val

    def save_incident(
        self,
        base_name: str,
        inc_hash: str,
        etime: str,
        ttl_days: int = 7
    ):
        daily_key = self._get_daily_key(base_name)

        self.client.hset(
            daily_key,
            inc_hash,
            etime
        )

        self.client.expire(
            daily_key,
            ttl_days * 24 * 3600
        )

    # ==========================================================
    # CORRELATION GROUPS
    # ==========================================================

    CORRELATION_PREFIX = "siem:correlation"

    def make_correlation_hash(
        self,
        source_ip: str | None,
        attack: str | None,
        origin_name: str | None,
    ) -> str:

        raw = "|".join([
            source_ip or "",
            attack or "",
            origin_name or "",
        ])

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def get_correlation_key(
        self,
        correlation_hash: str
    ) -> str:

        return (
            f"{self.CORRELATION_PREFIX}:"
            f"{correlation_hash}"
        )

    def get_correlation_group(
        self,
        correlation_hash: str
    ) -> dict | None:

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

        # NX = создать только если ключ ещё существует
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

    def delete_correlation_group(
        self,
        correlation_hash: str
    ):

        key = self.get_correlation_key(correlation_hash)

        self.client.delete(key)

    def correlation_exists(
        self,
        correlation_hash: str
    ) -> bool:

        key = self.get_correlation_key(correlation_hash)

        return bool(self.client.exists(key))


redis_incident_manager = RedisIncidentManager(
    settings.REDIS_URL
)