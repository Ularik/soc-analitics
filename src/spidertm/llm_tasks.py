
import asyncio
import logging

from celery import shared_task

from src.LLM.qwen import get_answer_from_qwen
from src.telegram.telegram_logger import telegram_logger


logger = logging.getLogger(__name__)


@shared_task(
    name="llm.analyze_attack",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def analyze_attack_task(
    self,
    *,
    event_wrapper: dict,
):
    """
    Анализирует событие SIEM при помощи LLM
    и отправляет результат анализа в Telegram.
    """

    try:
        status = event_wrapper["status"]
        event = event_wrapper["data"]

        logger.info(
            "=== LLM ANALYSIS STARTED ==="
        )

        logger.info(
            "Анализ события: status=%s, IP=%s",
            status,
            event.get("s_ip"),
        )


        # Celery task синхронная, поэтому запускаем
        # асинхронную функцию через asyncio.run()
        report = asyncio.run(
            get_answer_from_qwen(event)
        )

        logger.info(
            "LLM успешно завершила анализ: IP=%s",
            event.get("s_ip"),
        )

        # Отправляем второй Telegram message
        telegram_logger.send_analysis(
            report=report,
        )

        logger.info(
            "=== LLM ANALYSIS FINISHED ==="
        )

        return {
            "status": "analyzed",
            "ip": event.get("s_ip"),
        }

    except Exception as exc:
        logger.exception(
            "Ошибка при LLM-анализе события"
        )

        raise self.retry(exc=exc)

