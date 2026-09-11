import aio_pika
from src.config import settings

class RabbitCeleryClient:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection = None
        self._channel = None

    async def __aenter__(self):
        # Всегда открываем чистое соединение для текущего Event Loop
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self._channel = await self.connection.channel()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Закрываем сначала канал, затем соединение
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        # Обнуляем ссылки, чтобы не оставлять «мусор»
        self._channel = None
        self.connection = None

    async def publish(self, routing_key: str, message_id: str, message: str):
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=message.encode(),
                message_id=message_id
            ),
            routing_key=routing_key
        )

rbmq_celery = RabbitCeleryClient(settings.RMQ_URL)