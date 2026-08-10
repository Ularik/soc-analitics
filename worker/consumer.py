import json
import httpx
import aio_pika
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.database import AsyncSession
from src.models.models import Reports, ReportDelivery
from contextlib import asynccontextmanager
from src.config import settings

MAX_RETRIES = 10

@asynccontextmanager
async def get_session():
    async with AsyncSession() as session:
        yield session

async def process_report(message: aio_pika.IncomingMessage):
    data = json.loads(message.body)
    report_id = int(data["report_id"])

    async with get_session() as session:
        result = await session.execute(
            select(Reports, ReportDelivery)
            .options(joinedload(Reports.organization))
            .join(ReportDelivery, ReportDelivery.report_id == Reports.id)
            .where(Reports.id == report_id)
        )
        row = result.first()
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
                await message.reject(requeue=False)  # в reports.send.dead
            else:
                await session.commit()
                await message.reject(requeue=False)  # в reports.send.retry через DLX