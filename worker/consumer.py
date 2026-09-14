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
        row = await ReportsRepository(session).get_report_with_report_delivery_or_none(report_id)
        if row is None:
            await message.ack()
            return
        report, delivery = row

        if delivery.status == "sent":
            await message.ack()
            return

        try:
            body = {
                'username': 'daniyar',
                'organization': report.organization.name_en,
                'name': report.attack_type
            }

            if report.user is not None:
                body['username'] = report.user.username

            data = {
                'body': json.dumps(body)
            }

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

        except AttributeError as exc:
            logger.exception("Ошибка обработки report_id=%s: %s", report_id, exc)
            delivery.status = "failed"
            delivery.last_error = str(exc)  # сейчас это поле тут вообще не заполняется
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

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            logger.exception("Ошибка обработки report_id=%s: %s", report_id, exc)
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

