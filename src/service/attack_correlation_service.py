import logging

from src.redis.init import redis_manager
from src.schemas.detection_events_schemas import CorrelationGroup
from src.utils.extract_data import _extract_event_item

logger = logging.getLogger(__name__)

CORRELATION_WINDOW = 20 * 60
CORRELATION_TTL = CORRELATION_WINDOW + 10 * 60


def build_correlation_hash(
        source_ip: str,
        origin_name: str | None,
) -> str:
    return redis_manager.make_correlation_hash(
        source_ip=source_ip,
        origin_name=origin_name,
    )


def add_event_to_correlation_group(
        *,
        correlation_hash: str,
        event_log: dict,
        attack_name: str,
        origin_name: str | None,
        event_hash: str,
) -> bool:
    # 1. Получаем группу из Redis и восстанавливаем через Pydantic (если есть)
    raw_group = redis_manager.get_correlation_group(correlation_hash)
    group = CorrelationGroup.model_validate(raw_group) if raw_group else None

    # 2. Собираем объект текущего события
    event_item = _extract_event_item(event_log, attack_name, event_hash)

    # 3. Дедупликация (проверка последнего события)
    if group and group.events:
        last_event = group.events[-1]
        if (
                last_event.attack_name == event_item.attack_name and
                last_event.destination_ip == event_item.destination_ip and
                last_event.destination_port == event_item.destination_port
        ):
            logger.info("Повторяющееся событие не обрабатываем")
            return False

    event_time = event_item.event_time

    # ==========================================================
    # НОВАЯ ГРУППА
    # ==========================================================
    if group is None:
        group = CorrelationGroup(
            correlation_hash=correlation_hash,
            source_ip=event_log.get("s_ip"),
            source_country=event_log.get("s_country"),
            origin_name=origin_name,
            first_event_time=event_time,
            last_event_time=event_time,
            count=1,
            events=[event_item],
        )

        redis_manager.create_correlation_group(
            correlation_hash,
            group.model_dump(),
            ttl=CORRELATION_TTL,
        )

        return True

    # ==========================================================
    # СУЩЕСТВУЮЩАЯ ГРУППА
    # ==========================================================
    group.count += 1
    group.last_event_time = event_time
    group.events.append(event_item)

    redis_manager.save_correlation_group(
        correlation_hash,
        group.model_dump(),
        ttl=CORRELATION_TTL,
    )

    return True


def add_unique(target: list, value):
    if value is not None and value not in target:
        target.append(value)
