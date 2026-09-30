import asyncio
import json
import logging
from datetime import datetime, timezone
import aio_pika
import httpx

from src.config import settings
from src.database import Session
from src.repositories.reports_repository import ReportsRepository

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _get_report_data_sync(report_id: int):
    """Синхронный запрос данных из БД."""
    with Session() as session:
        # Вызываем существующий метод вашего репозитория
        row = ReportsRepository(session).get_report_with_report_delivery_or_none(report_id)
        if not row:
            return None
        report, delivery = row

        # Извлекаем необходимые данные, чтобы использовать их вне сессии
        return {
            "delivery_id": delivery.id,
            "delivery_status": delivery.status,
            "delivery_retry_count": delivery.retry_count,
            "idempotency_key": str(delivery.idempotency_key),
            "username": report.user.username if report.user else "daniyar",
            "organization_name": report.organization.name_en,
            "attack_type": report.attack_type,
            "file_name": report.file_name,
            "file_content": report.file_content,
        }


def _update_delivery_sync(report_id: int, status: str, retry_count: int = None, last_error: str = None):
    """Синхронное обновление статуса доставки в БД через существующий метод."""
    with Session() as session:
        repo = ReportsRepository(session)
        row = repo.get_report_with_report_delivery_or_none(report_id)
        if row:
            _, delivery = row
            delivery.status = status
            if status == "sent":
                delivery.sent_at = datetime.now(timezone.utc)
            if retry_count is not None:
                delivery.retry_count = retry_count
            if last_error is not None:
                delivery.last_error = str(last_error)[:1000]
            session.commit()


async def process_report(
        message: aio_pika.IncomingMessage,
        channel: aio_pika.Channel
):
    try:
        data = json.loads(message.body)
        report_id = int(data["report_id"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("Невалидный JSON или отсутствует report_id: %s", exc)
        await message.ack()
        return

    # 1. Получаем данные из синхронной БД без блокировки Event Loop
    report_data = await asyncio.to_thread(_get_report_data_sync, report_id)
    if not report_data:
        await message.ack()
        return

    if report_data["delivery_status"] == "sent":
        await message.ack()
        return

    try:
        body = {
            'username': report_data["username"],
            'organization': report_data["organization_name"],
            'name': report_data["attack_type"]
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.CERT_GOV}/api/router/report-create",
                data={'body': json.dumps(body)},
                files={"file": (report_data["file_name"], report_data["file_content"], "application/pdf")},
                headers={"Idempotency-Key": report_data["idempotency_key"]},
            )
            response.raise_for_status()
            logger.info("Отправка отчета report_id=%s прошла успешно", report_id)

        # 2. Обновляем статус успешной отправки
        await asyncio.to_thread(
            _update_delivery_sync,
            report_id=report_id,
            status="sent",
        )
        await message.ack()

    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
        logger.warning("Ошибка сети/HTTP при отправке report_id=%s: %s", report_id, exc)
        new_retry_count = report_data["delivery_retry_count"] + 1

        if new_retry_count >= MAX_RETRIES:
            await asyncio.to_thread(
                _update_delivery_sync,
                report_id=report_id,
                status="failed",
                retry_count=new_retry_count,
                last_error=str(exc),
            )
            # Отправка в Dead Letter Exchange (DLX)
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
            await asyncio.to_thread(
                _update_delivery_sync,
                report_id=report_id,
                status="processing",
                retry_count=new_retry_count,
                last_error=str(exc),
            )
            # Использование nack() вместо reject()
            await message.nack(requeue=False)

    except Exception as exc:
        logger.exception("Непредвиденная ошибка при обработке report_id=%s: %s", report_id, exc)
        await asyncio.to_thread(
            _update_delivery_sync,
            report_id=report_id,
            status="failed",
            last_error=str(exc),
        )
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message.body,
                headers=message.headers,
                delivery_mode=message.delivery_mode,
            ),
            routing_key="reports.send.dead",
        )
        await message.ack()