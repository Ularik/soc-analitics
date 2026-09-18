import logging

from src.redis.sync_redis import redis_incident_manager

logger = logging.getLogger(__name__)

CORRELATION_TTL = 30


def build_correlation_hash(
    source_ip: str,
    attack_name: str,
    origin_name: str | None,
) -> str:

    return redis_incident_manager.make_correlation_hash(
        source_ip=source_ip,
        attack=attack_name,
        origin_name=origin_name,
    )


def add_event_to_correlation_group(
    *,
    correlation_hash: str,
    event_log: dict,
    attack_name: str,
    origin_name: str | None,
    event_hash: str,
    status: str,
) -> tuple[dict, bool]:

    group = redis_incident_manager.get_correlation_group(
        correlation_hash
    )

    event_time = event_log.get("event_time")

    event_data = {
        "event_hash": event_hash,
        "event_time": event_time,
        "destination_ip": event_log.get("d_ip"),
        "destination_port": event_log.get("d_port"),
        "source_port": event_log.get("s_port"),
        "status": status,
    }

    # ==========================================================
    # НОВАЯ ГРУППА
    # ==========================================================

    if group is None:

        group = {   # Сюда pydantic схему воткнуть
            "correlation_hash": correlation_hash,

            "source_ip": event_log.get("s_ip"),
            "attack": attack_name,
            "origin_name": origin_name,

            "first_event_time": event_time,
            "last_event_time": event_time,

            "count": 1,

            "destination_ips": [],
            "destination_ports": [],
            "source_ports": [],

            "events": [],
        }

        add_unique(
            group["destination_ips"],
            event_log.get("d_ip"),
        )

        add_unique(
            group["destination_ports"],
            event_log.get("d_port"),
        )

        add_unique(
            group["source_ports"],
            event_log.get("s_port"),
        )

        group["events"].append(event_data)

        created = redis_incident_manager.create_correlation_group(
            correlation_hash,
            group,
            ttl=CORRELATION_TTL,
        )

        return group, created

    # ==========================================================
    # СУЩЕСТВУЮЩАЯ ГРУППА
    # ==========================================================

    group["count"] += 1

    group["last_event_time"] = event_time

    add_unique(
        group["destination_ips"],
        event_log.get("d_ip"),
    )

    add_unique(
        group["destination_ports"],
        event_log.get("d_port"),
    )

    add_unique(
        group["source_ports"],
        event_log.get("s_port"),
    )

    group["events"].append(event_data)

    redis_incident_manager.save_correlation_group(
        correlation_hash,
        group,
        ttl=CORRELATION_TTL,
    )

    return group, False


def add_unique(target: list, value):

    if value is not None and value not in target:
        target.append(value)