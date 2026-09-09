import logging

from celery import shared_task

from src.telegram.telegram_logger import telegram_logger


logger = logging.getLogger(__name__)


@shared_task(
    name="telegram.send_attack_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_telegram_attack_task(
    self,
    *,
    event_wrapper: dict,
):
    try:
        status = event_wrapper["status"]
        event = event_wrapper["data"]

        ip = event.get("s_ip")
        rule_name = event.get("rulename", "").strip()
        node = event.get("d_info")
        attempts = event.get("cnt")

        success = telegram_logger.send_attack(
            status=status,
            ip=ip,
            rule_name=rule_name,
            node=node,
            attempts=attempts,
        )

        if not success:
            raise RuntimeError(
                "Telegram не подтвердил отправку сообщения"
            )

        return {
            "status": "sent",
            "ip": ip,
        }

    except Exception as exc:
        logger.exception(
            "Ошибка отправки уведомления в Telegram"
        )

        raise self.retry(exc=exc)