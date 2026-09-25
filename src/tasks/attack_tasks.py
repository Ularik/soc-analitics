import asyncio
import logging
import time
from celery import shared_task

from src.redis.init import redis_manager
from src.tasks.llm_tasks import _process_analysis_and_report_async
from src.telegram.telegram_logger import telegram_logger
from src.tasks.utils import build_attack_prompt


logger = logging.getLogger(__name__)

CORRELATION_WINDOW = 20 * 60

@shared_task(
    name="src.tasks.attack_tasks.finalize_attack_group"
)
def finalize_attack_group(
    correlation_hash: str
):

    group = redis_manager.get_correlation_group(
        correlation_hash
    )

    if group is None:
        logger.info(
            f"Группа уже обработана: "
            f"{correlation_hash}"
        )
        return
    elapsed = time.time() - group["last_seen_at"]

    if elapsed < CORRELATION_WINDOW:
        # пока эта задача ждала countdown, пришли новые события —
        # атака ещё не затихла. Реальную работу сделает более поздний
        # вызов finalize, который был запланирован при том новом событии
        return

    logger.info(
        f"Группа готова к анализу {correlation_hash}: "
        f"{group['count']} событий"
    )
    analyze_attack_group.delay(
        correlation_hash,
        delete_group=True,
    )


@shared_task(
    name="src.tasks.attack_tasks.analyze_attack_group",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def analyze_attack_group(
    self,
    correlation_hash: str,
    delete_group: bool = True,
):
    group = redis_manager.get_correlation_group(correlation_hash)

    if group is None:
        logger.info(f"Группа уже удалена: {correlation_hash}")
        return

    try:
        logger.info(
            f"Запускаем LLM-анализ группы {correlation_hash}: "
            f"{group['count']} событий"
        )

        report = asyncio.run(
            _process_analysis_and_report_async(
                prompt=build_attack_prompt(group),
            )
        )

        if not telegram_logger.send_analysis(report=report):
            raise RuntimeError("Telegram не подтвердил отправку анализа")

        if delete_group:
            redis_manager.delete_correlation_group(correlation_hash)
            logger.info(f"Группа обработана и удалена: {correlation_hash}")

        return {
            "status": "analyzed_and_sent",
            "correlation_hash": correlation_hash,
        }

    except Exception as exc:
        logger.exception(
            f"Ошибка обработки группы {correlation_hash}: {exc}"
        )
        raise self.retry(exc=exc)
