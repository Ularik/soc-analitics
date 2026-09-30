from datetime import datetime
import json
import logging
import uuid

from src.LLM.init import get_answer_from_gemini
from src.LLM.qwen import get_answer_from_qwen
from src.redis.init import redis_manager
from src.schemas.reports_schemas import (
    ReportCreateSchema,
    ReportDeliverySchema,
    ReportGenerateSchema,
)
from src.service.base import BaseService
from src.utils.cache_key_builder import custom_log_key_builder
from src.utils.get_pdf_file import generate_report_pdf

logger = logging.getLogger(__name__)


class ReportsService(BaseService):

    def get_answer_from_ai(self, body: str) -> ReportGenerateSchema:
        key = custom_log_key_builder(body)
        cached_body = redis_manager.get(key)

        if cached_body is not None:
            return ReportGenerateSchema.model_validate_json(cached_body)

        answer = get_answer_from_gemini(body)

        redis_manager.set(key, answer.model_dump_json(), expire=60)
        return answer

    def get_reports(self):
        result = self.db.reports.get_reports()
        return result

    def create_report(
        self, body: ReportGenerateSchema, user_id: int | None = None
    ) -> int:
        # Прямой синхронный вызов без asyncio.to_thread
        pdf_buffer = generate_report_pdf(body)
        pdf_bytes = pdf_buffer.getvalue()

        _data = ReportCreateSchema(
            **body.model_dump(),
            user_id=user_id,
            file_content=pdf_bytes,
            file_name=f"{body.origin_name}-{datetime.now():%Y%m%d_%H%M%S}.pdf",
        )
        report = self.db.reports.create_report(_data)
        idempotency_key = str(uuid.uuid4())

        delivery_data = ReportDeliverySchema(
            report_id=report.id, status="pending", idempotency_key=idempotency_key
        )
        self.db.reports.create_reports_delivery(delivery_data)
        self.db.save()
        self._send_report(report.id)
        return report.id

    def _send_report(self, report_id: int):
        message_body = {
            "report_id": str(report_id),
        }

        logger.info(
            "RABBIT: publishing report_id=%s routing_key=%s",
            report_id,
            "reports.send",
        )

        self.rmq_channel.publish(
            message=json.dumps(message_body),
            message_id=str(report_id),
            routing_key="reports.send",
        )

        logger.info(
            "RABBIT: publish completed report_id=%s",
            report_id,
        )