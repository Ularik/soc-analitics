from src.schemas.detection_events_schemas import DetectionNoticeResponse
from src.redis.sync_redis import redis_manager
import ipaddress
import logging

logger = logging.getLogger(__name__)

REDIS_INCIDENTS_KEY = "siem:processed_incidents"


def is_request_new(detection_schema: DetectionNoticeResponse) -> list[dict]:
    """
    Сверяет трафик со старыми запросами и удаляет повторяющиеся.
    """
    notices = detection_schema.data.noticeList.result
    new_events = []

    for notice in notices:
        inc_hash = notice.incident_hash or notice.samefield_hash
        etime = str(notice.etime) if notice.etime else ""

        if not inc_hash:
            continue

        cached_etime = redis_manager.hget(name=REDIS_INCIDENTS_KEY, key=inc_hash)

        if cached_etime is not None:
            if cached_etime == etime:
                continue
            else:
                redis_manager.hset(name=REDIS_INCIDENTS_KEY, key=inc_hash, val=etime)
                new_events.append({"status": "UPDATED", "data": notice})
        else:
            redis_manager.hset(REDIS_INCIDENTS_KEY, inc_hash, etime)
            new_events.append({"status": "NEW", "data": notice})

    return new_events


def is_request_danger(event_log: dict) -> bool:
    src_ip_str = event_log.get("s_ip")

    if not src_ip_str:
        logger.warning("Системный трафик")
        return False

    try:
        ip_obj = ipaddress.ip_address(src_ip_str)

        if ip_obj.is_private:
            logger.info(f"Событие с локального IP ({src_ip_str}). Игнорируем.")
            return False
        else:
            return True

    except ValueError:
        logger.error(f"Некорректный формат IP-адреса: {src_ip_str}")
        return False