import json
import httpx
import aio_pika
from datetime import datetime
from src.database import AsyncSession
from src.repositories.reports_repository import ReportsRepository
from src.config import settings
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

async def process_report(
        message: aio_pika.IncomingMessage,
        channel: aio_pika.Channel
):
    data = json.loads(message.body)
    report_id = int(data["report_id"])

    async with AsyncSession() as session:
        repository = ReportsRepository(session)
        row = await repository.get_report_with_report_delivery_or_none(report_id)
        if row is None:
            await message.ack()
            return
        report, delivery = row

        if delivery.status == "sent":
            await message.ack()
            return

        data = {
            'body': json.dumps({
                'organization': report.organization.name_en,
                'name': report.attack_type
            })
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{settings.CERT_GOV}/api/router/report-create",
                    data=data,
                    files={"file": (report.file_name, report.file_content, "application/pdf")},
                    headers={"Idempotency-Key": str(delivery.idempotency_key)},
                )
                response.raise_for_status()
                logger.info("Отправка сообщения прошла успешно")
            delivery.status = "sent"
            delivery.sent_at = datetime.now()
            await session.commit()
            await message.ack()

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            delivery.retry_count += 1
            delivery.last_error = str(exc)
            if delivery.retry_count >= MAX_RETRIES:
                delivery.status = "failed"
                await session.commit()

                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message.body,
                        headers=message.headers,
                        delivery_mode=message.delivery_mode,
                    ),
                    routing_key="reports.send.dead",
                )
                await message.ack()
            else:
                await session.commit()
                await message.reject(requeue=False)  # в reports.send.retry через DLX