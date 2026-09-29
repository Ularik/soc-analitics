from src.schemas.detection_events_schemas import DetectionNoticeResponse, FilteredDetectionEventSchema, \
    DetectionEventSchema
from src.redis.init import redis_manager
import ipaddress
import logging

logger = logging.getLogger(__name__)


REDIS_INCIDENTS_KEY = "siem:processed_incidents"


def is_request_new(
    detection_schema: DetectionNoticeResponse
) -> list[FilteredDetectionEventSchema]:

    notices = detection_schema.data.noticeList.result

    new_events = []

    for notice in notices:

        event_log = notice.parse_line()

        inc_hash = (
            notice.incident_hash
            or notice.samefield_hash
        )

        if not inc_hash:
            continue

        if not event_log.get("event_time"):
            continue

        cached_event = redis_manager.get_incident_etime(
            base_name=REDIS_INCIDENTS_KEY,
            inc_hash=inc_hash,
        )

        if cached_event is not None:
            logger.info(
                f"Событие уже обработано: {inc_hash}"
            )
            continue

        new_events.append(
            FilteredDetectionEventSchema(
                data=notice,
                event_hash=inc_hash,
            )
        )

    return new_events


def is_remote_ip(event: DetectionEventSchema) -> bool:
    event_log = event.parse_line()
    src_ip_str = event_log.get('s_ip')

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

