import json

from src.schemas.detection_events_schemas import DetectionNoticeResponse
from src.redis.sync_redis import redis_incident_manager
import ipaddress
from datetime import date
import logging

logger = logging.getLogger(__name__)

REDIS_INCIDENTS_KEY = "siem:processed_incidents"


def is_request_new(
    detection_schema: DetectionNoticeResponse
) -> list[dict]:

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

        cached_event = redis_incident_manager.get_incident_etime(
            base_name=REDIS_INCIDENTS_KEY,
            inc_hash=inc_hash,
        )

        if cached_event is not None:
            logger.info(
                f"Событие уже обработано: {inc_hash}"
            )
            continue

        # Сохраняем конкретное событие
        redis_incident_manager.save_incident(
            base_name=REDIS_INCIDENTS_KEY,
            inc_hash=inc_hash,
            etime=event_log["event_time"],
        )

        new_events.append({
            "status": "NEW",
            "data": notice,
            "event_hash": inc_hash,
        })

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


def build_attack_prompt(group: dict) -> str:

    return f"""
Проанализируй агрегированное событие информационной безопасности.

Источник:
{group["source_ip"]}

Правило обнаружения:
{group["attack"]}

Средство обнаружения:
{group["origin_name"]}

Первое событие:
{group["first_event_time"]}

Последнее событие:
{group["last_event_time"]}

Количество событий:
{group["count"]}

Уникальные IP назначения:
{group["destination_ips"]}

Порты назначения:
{group["destination_ports"]}

Порты источника:
{group["source_ports"]}

Отдельные события:
{group["events"]}

Не анализируй бинарные данные, Base64,
pcap и длинные payload.
Используй только значимые признаки атаки.

Сделай итоговый SOC-анализ.
"""