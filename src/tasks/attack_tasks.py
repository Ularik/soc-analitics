import logging
from celery import shared_task

from src.rabbitmq.init import rabbit_client
from src.service.reports_service import ReportsService
from src.database import Session
from src.db_manager.db_manager import DbManager
from src.redis.init import redis_manager
from src.schemas.reports_schemas import ReportGenerateSchema
from src.LLM.init import get_answer_from_gemini
from src.telegram.telegram_logger import telegram_logger


logger = logging.getLogger(__name__)

CORRELATION_WINDOW = 20 * 60


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
        logger.info(f"Группа уже удалена или не существует: {correlation_hash}")
        return {
            "status": "not_found",
            "correlation_hash": correlation_hash,
        }

    try:
        logger.info(
            f"Запускаем LLM-анализ группы {correlation_hash}: "
            f"{group.get('count', 0)} событий"
        )

        # Вызываем синхронную функцию напрямую без asyncio.run()
        report: ReportGenerateSchema = get_answer_from_gemini(group)

        # Отправка отчета (передаем Pydantic модель или dict в зависимоcти от telegram_logger)
        if not telegram_logger.send_analysis(report=report):
            raise RuntimeError("Telegram не подтвердил отправку анализа")

        with DbManager(session_factory=Session) as db:
            with rabbit_client as channel:
                ReportsService(db, rabbit_mq=channel).create_report(body=report)

        if delete_group:
            redis_manager.delete_correlation_group(correlation_hash)
            logger.info(f"Группа успешно обработана и удалена: {correlation_hash}")

        return {
            "status": "analyzed_and_sent",
            "correlation_hash": correlation_hash,
        }

    except Exception as exc:
        logger.exception(
            f"Ошибка обработки группы {correlation_hash}: {exc}"
        )
        raise self.retry(exc=exc)
