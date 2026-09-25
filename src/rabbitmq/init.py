import pika
from src.config import settings


class RabbitClient:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection = None
        self._channel = None

    def connect(self):
        if not self.connection or self.connection.is_closed:
            parameters = pika.URLParameters(self.amqp_url)
            self.connection = pika.BlockingConnection(parameters)

    def __enter__(self):
        if not self.connection or self.connection.is_closed:
            self.connect()
        self._channel = self.connection.channel()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._channel and self._channel.is_open:
            self._channel.close()

    def publish(self, routing_key: str, message_id: str, message: str):
        properties = pika.BasicProperties(message_id=message_id)

        # default exchange в pika обозначается пустой строкой ''
        self._channel.basic_publish(
            exchange='',
            routing_key=routing_key,
            body=message.encode('utf-8'),
            properties=properties
        )

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()


rabbit_client = RabbitClient(settings.RMQ_URL)