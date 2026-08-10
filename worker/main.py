import asyncio
import signal
import aio_pika
from worker.queues import setup_queues
from worker.consumer import process_report
import sys

async def main():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)
    await setup_queues(channel)

    queue = await channel.get_queue("reports.send")
    consumer_tag = await queue.consume(process_report)
    print("Worker started, waiting for messages...")

    stop_event = asyncio.Event()
    def _handle_stop(*_args):
        stop_event.set()

    if sys.platform == "win32":
        # На Windows add_signal_handler не реализован — используем обычный signal.signal
        signal.signal(signal.SIGINT, _handle_stop)
        if hasattr(signal, "SIGBREAK"):  # Ctrl+Break на Windows
            signal.signal(signal.SIGBREAK, _handle_stop)
    else:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _handle_stop)

    await stop_event.wait()
    print("Shutting down gracefully...")
    await queue.cancel(consumer_tag)
    await connection.close()

if __name__ == "__main__":
    asyncio.run(main())