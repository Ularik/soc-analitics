from src.service.base import BaseService
from src.utils.cache_key_builder import custom_log_key_builder
from src.schemas.reports_schemas import ReportCreateSchema, ReportGenerateSchema, ReportDeliverySchema
from src.redis.init import redis_manager
from src.gemini.init import get_answer_from_gemini
import uuid
from src.utils.get_pdf_file import generate_report_pdf
import asyncio
from datetime import datetime
from src.rabbitmq.init import RabbitClient
import json


class ReportsService(BaseService):

    async def get_answer_from_ai(self, body: str) -> ReportGenerateSchema:
        key = custom_log_key_builder(body)
        cached_body = await redis_manager.get(key)

        if cached_body is not None:
            return ReportGenerateSchema.model_validate_json(cached_body)

        answer = await get_answer_from_gemini(body)

        await redis_manager.set(key, answer.model_dump_json(), expire=20)
        return answer

    async def get_reports(self):
        result = await self.db.reports.get_reports()
        return result

    async def create_report(self, body: ReportGenerateSchema) -> int:   # добавить rabbitmq
        pdf_buffer = await asyncio.to_thread(generate_report_pdf, body)
        pdf_bytes = pdf_buffer.getvalue()

        _data = ReportCreateSchema(
            **body.model_dump(),
            file_content=pdf_bytes,
            file_name=f"{body.origin_name}-{datetime.now():%Y%m%d_%H%M%S}.pdf"
        )
        report = await self.db.reports.create_report(_data)
        idempotency_key = uuid.uuid4()

        delivery_data = ReportDeliverySchema(report_id=report.id, status='pending', idempotency_key=idempotency_key)
        await self.db.reports.create_reports_delivery(delivery_data)
        await self.db.save()
        await self._send_report(report.id)
        return report.id

    async def _send_report(self, report_id: int):
        message_body = {
            "report_id": str(report_id),
        }
        await self.rmq_channel.publish(
            message=json.dumps(message_body),
            message_id=str(report_id),
            routing_key="reports.send",
        )