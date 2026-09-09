import ipaddress
import logging
from celery import shared_task
from src.spidertm.telegram_tasks import send_telegram_attack_task
from src.spidertm.sync_redis import redis_manager
from src.spidertm.client_session import siem_client
from src.spidertm.llm_tasks import analyze_attack_task


logger = logging.getLogger(__name__)
REDIS_INCIDENTS_KEY = "siem:processed_incidents"


def process_notices(json_data: dict) -> list[dict]:
    notices = json_data.get("data", {}).get("noticeList", {}).get("result", [])
    new_events = []

    for notice in notices:
        inc_hash = notice.get("incident_hash") or notice.get("samefield_hash")
        etime = str(notice.get("etime", ""))

        if not inc_hash:
            continue

        # Синхронное получение из Redis
        cached_etime = redis_manager.hget(REDIS_INCIDENTS_KEY, inc_hash)

        if cached_etime is not None:
            if cached_etime == etime:
                continue
            else:
                redis_manager.hset(REDIS_INCIDENTS_KEY, inc_hash, etime)
                new_events.append({"status": "UPDATED", "data": notice})
        else:
            redis_manager.hset(REDIS_INCIDENTS_KEY, inc_hash, etime)
            new_events.append({"status": "NEW", "data": notice})

    return new_events


def inspect_event_ip(event_wrapper: dict):
    status = event_wrapper["status"]
    event = event_wrapper["data"]
    src_ip_str = event.get("s_ip")

    if not src_ip_str:
        logger.warning("В событии отсутствует поле s_ip.")
        return

    try:
        ip_obj = ipaddress.ip_address(src_ip_str)

        if not ip_obj.is_private:
            logger.warning(
                f"[!] ОБНАРУЖЕНА ВНЕШНЯЯ АТАКА [{status}] с IP: {src_ip_str} | "
                f"Правило: {event.get('rulename', '').strip()} | "
                f"Узел: {event.get('d_info')} | Попыток: {event.get('cnt')}"
            )

            # Здесь можно отправлять нотификацию в Telegram / Инцидент-менеджер
            send_telegram_attack_task.delay(
                event_wrapper=event_wrapper,
            )
            analyze_attack_task.delay(event_wrapper=event_wrapper)

        else:
            logger.info(f"Событие [{status}] с локального IP ({src_ip_str}). Игнорируем.")

    except ValueError:
        logger.error(f"Некорректный формат IP-адреса: {src_ip_str}")


@shared_task(name="tasks.process_siem_events_task")
def process_siem_events_task():
    try:
        # Переиспользует существующий TCP HTTP Keep-Alive сокет и cookie авторизации
        json_data = siem_client.fetch_events()
    except Exception as e:
        logger.error(f"Не удалось получить данные из SIEM: {e}")
        return

    unprocessed_events = process_notices(json_data)

    if not unprocessed_events:
        logger.info("Новых событий не найдено.")
        return

    for event_wrapper in unprocessed_events:
        inspect_event_ip(event_wrapper)