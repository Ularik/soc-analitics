
import asyncio
import logging

from celery import shared_task

from src.db_manager.db_manager import DbManager
from src.rabbitmq.init import rabbit_client
from src.schemas.reports_schemas import ReportGenerateSchema
from src.service.reports_service import ReportsService
from src.database import AsyncSession
from src.LLM.qwen import get_answer_from_qwen
from src.LLM.init import get_answer_from_gemini
from src.schemas.detection_events_schemas import DetectionEventSchema
from src.telegram.telegram_logger import telegram_logger


logger = logging.getLogger(__name__)

async def _process_analysis_and_report_async(prompt: str) -> ReportGenerateSchema:
    """
    Асинхронный хелпер: выполняет запросы к LLM, БД и RabbitMQ
    в рамках единого event loop Celery-задачи.
    """
    # 1. Получаем анализ от LLM (асинхронно)
    report_schema = await get_answer_from_gemini(prompt)

    # 2. Инициализируем БД и RabbitMQ клиент для создания и отправки отчета
    async with DbManager(session_factory=AsyncSession) as db:
        # Важно: создаем/получаем асинхронный канал RabbitMQ в текущем loop
        async with rabbit_client as channel:
            service = ReportsService(db=db, rabbit_mq=channel)
            await service.create_report(body=report_schema)

    return report_schema

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
        event = DetectionEventSchema.model_validate(event_wrapper["data"])

        # Извлекаем IP через вызов .s_ip
        ip = event.s_ip

        logger.info("=== LLM ANALYSIS STARTED ===")
        logger.info(
            "Анализ события: status=%s, IP=%s",
            status,
            ip,
        )

        # Передаем словарь модели в LLM
        prompt = event.line
        report = asyncio.run(
            _process_analysis_and_report_async(
                prompt=prompt,
            )
        )

        logger.info(
            "LLM успешно завершила анализ: IP=%s",
            ip,
        )

        telegram_logger.send_analysis(
            report=report,
        )

        logger.info("=== LLM ANALYSIS FINISHED ===")

        return {
            "status": "analyzed",
            "ip": ip,
        }

    except Exception as exc:
        logger.exception("Ошибка при LLM-анализе события")
        raise self.retry(exc=exc)