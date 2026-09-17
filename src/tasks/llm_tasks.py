
import asyncio
import logging
from pprint import pprint
import datetime
from celery import shared_task

from src.db_manager.db_manager import DbManager
from src.rabbitmq.rabbit_for_celery import rbmq_celery
from src.schemas.reports_schemas import ReportGenerateSchema
from src.service.reports_service import ReportsService
from src.database import AsyncSessionNullPool
from src.LLM.qwen import get_answer_from_qwen
from src.LLM.init import get_answer_from_gemini
from src.schemas.detection_events_schemas import DetectionEventSchema
from src.telegram.telegram_logger import telegram_logger


logger = logging.getLogger(__name__)

event_data = {
    "origin_name": "President ADM_01.TMS Sensor(IPS)",
    "source_ip": "66.240.205.34",
    "host": None,
    "detection_tool": "IPS",
    "methods": "Malware Hunter Shodan RAT Scanner(TCP)-1",
    "risk_assessment": "Высокая",
    "country": "US",
    "detection_date": datetime.datetime(2026, 9, 14, 11, 28, 42, 943000),
    "attack_type": "Malware Hunter Shodan RAT Scanner(TCP)-1",
    "destination_ip": "212.42.102.94",
    "cve": "N/A",
    "protocols_ports": "TCP/33338",
    "potential_impact": (
        "Сканирование системы с целью выявления подконтрольных RAT-сервисов и"
        " открытых портов. В случае нахождения уязвимых или скомпрометированных"
        " служб возможен несанкционированный доступ к узлу и захват управления"
        " операционной системой."
    ),
    "data_or_payload": (
        "SYN-пакет (pcap len 60B):"
        " 1MOyoQIABAAAAAAAAAAAAP//AAABAAAADoanapEnCwA8AAAAPAAAALyNHyFqpCiiS3OJmAgARZgALDtKAABpBstOQvDNItQqZl5G9II6j4X+4wAAAABgAi08yLYAAAIEBbQAAA=="
    ),
    "short_description": (
        "Обнаружена разведывательная активность автоматизированного сканера"
        " Shodan Malware Hunter, направленная на поиск активных сред RAT. Вектор"
        " атаки представляет собой одиночный TCP SYN-запрос на порт 33338. Запрос"
        " был зафиксирован сетевым IPS в режиме пропуска (ALLOW)."
    ),
    "response_actions": (
        "1. Блокировка IP-адреса источника 66.240.205.34 на периметральном"
        " межсетевом экране. 2. Проверка состояния хоста 212.42.102.94 на"
        " наличие открытых портов и несанкционированных процессов. 3. Проведение"
        " антивирусного сканирования целевой системы на предмет присутствия"
        " вредоносного ПО и RAT. 4. Изменение действия сигнатуры в IPS с ALLOW"
        " на BLOCK. 5. Анализ логов на наличие аналогичной активности из подсетей"
        " сканеров Shodan."
    ),
}

async def _process_analysis_and_report_async(prompt: str) -> ReportGenerateSchema:
    """
    Асинхронный хелпер: выполняет запросы к LLM, БД и RabbitMQ
    в рамках единого event loop Celery-задачи.
    """
    # 1. Получаем анализ от LLM (асинхронно)
    report_schema = await get_answer_from_gemini(prompt)

    # 2. Инициализируем БД и RabbitMQ клиент для создания и отправки отчета
    async with DbManager(session_factory=AsyncSessionNullPool) as db:
        # Важно: создаем/получаем асинхронный канал RabbitMQ в текущем loop
        async with rbmq_celery as channel:
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