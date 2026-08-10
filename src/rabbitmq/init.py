import aio_pika
from src.config import settings

class RabbitClient:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection = None
        self._channel = None

    async def connect(self):
        if not self.connection or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(self.amqp_url)

    async def __aenter__(self):
        self._channel = await self.connection.channel()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._channel and not self._channel.is_closed:
            await self._channel.close()

    async def publish(self, routing_key: str, message_id: str, message: str):
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=message.encode(),
                message_id=message_id
            ),
            routing_key = routing_key
        ),

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


rabbit_client = RabbitClient(settings.RMQ_URL)