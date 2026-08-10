import aio_pika

async def setup_queues(channel: aio_pika.Channel):
    await channel.declare_queue(
        "reports.send.retry", durable=True,
        arguments={
            "x-message-ttl": 30000,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "reports.send",
        },
    )
    await channel.declare_queue(
        "reports.send", durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "reports.send.retry",
        },
    )
    await channel.declare_queue("reports.send.dead", durable=True)