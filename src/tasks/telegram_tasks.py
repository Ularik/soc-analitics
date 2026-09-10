import logging

from celery import shared_task

from src.schemas.detection_events_schemas import DetectionEventSchema
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
        # Десериализуем данные обратно в Pydantic-модель
        event = DetectionEventSchema.model_validate(event_wrapper["data"])

        # Извлекаем IP через вызов .s_ip (который читает внутри line)
        ip = event.s_ip
        rule_name = event.rulename.strip()
        node = event.d_info
        attempts = event.cnt

        success = telegram_logger.send_attack(
            status=status,
            ip=ip,
            rule_name=rule_name,
            node=node,
            attempts=attempts,
        )

        if not success:
            raise RuntimeError("Telegram не подтвердил отправку сообщения")

        return {
            "status": "sent",
            "ip": ip,
        }

    except Exception as exc:
        logger.exception("Ошибка отправки уведомления в Telegram")
        raise self.retry(exc=exc)