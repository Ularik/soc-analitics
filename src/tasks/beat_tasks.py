import logging
from celery import shared_task

from src.service.attack_correlation_service import build_correlation_hash, add_event_to_correlation_group, \
    CORRELATION_WINDOW
from src.tasks.utils import is_request_new, is_remote_ip
from src.spidertm.client_session import siem_client
from src.schemas.detection_events_schemas import DetectionNoticeResponse, DetectionEventSchema, \
    FilteredDetectionEventSchema
from src.tasks.attack_tasks import finalize_attack_group, analyze_attack_group

logger = logging.getLogger(__name__)


def group_events(event_wrapper: FilteredDetectionEventSchema):
    event: DetectionEventSchema = event_wrapper.data
    event_log = event.parse_line()
    event_hash: str = event_wrapper.event_hash

    src_ip_str = event_log.get("s_ip")
    attack_name = event.rulename.strip()
    origin_name = event_log.get(
        "origin_name"
    )
    logger.warning(
        f"[!] ОБНАРУЖЕНА ВНЕШНЯЯ АТАКА "
        f"с IP: {src_ip_str} | "
        f"Правило: {attack_name} | "
        f"Узел: {event.d_info} | "
        f"Попыток: {event.cnt}"
    )

    # ======================================================
    # CORRELATION
    # ======================================================

    correlation_hash = build_correlation_hash(
        source_ip=src_ip_str,
        attack_name=attack_name,
        origin_name=origin_name,
    )

    group, is_new_group = (
        add_event_to_correlation_group(
            correlation_hash=correlation_hash,
            event_log=event_log,
            attack_name=attack_name,
            origin_name=origin_name,
            event_hash=event_hash,
        )
    )

    logger.info(
        f"Корреляционная группа: "
        f"{correlation_hash} | "
        f"events={group['count']}"
    )

    # ======================================================
    # FIRST EVENT
    # ======================================================

    if is_new_group:
        analyze_attack_group.delay(correlation_hash, delete_group=False)

    # планируем на каждое событие, не только на новую группу
    finalize_attack_group.apply_async(
        args=[correlation_hash],
        countdown=CORRELATION_WINDOW,
    )


@shared_task(name="src.tasks.beat_tasks.process_siem_events_task")
def process_siem_events_task():

    try:
        detection_schema: DetectionNoticeResponse = (
            siem_client.fetch_events()
        )

    except Exception as e:
        logger.error(
            f"Не удалось получить данные из SIEM: {e}"
        )
        return

    new_events = is_request_new(
        detection_schema
    )

    if not new_events:
        logger.info(
            "Новых событий не найдено."
        )
        return

    for event_wrapper in new_events:

        if not is_remote_ip(event_wrapper.data):
            continue

        group_events(event_wrapper)