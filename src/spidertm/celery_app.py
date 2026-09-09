from celery import Celery
from celery.schedules import crontab
from src.config import settings

celery_instance = Celery(
    "spidertm",
    broker=settings.REDIS_URL,
    backend=f"rpc://",
)

celery_instance.conf.include = [
    "src.spidertm.tasks",
    "src.spidertm.telegram_tasks",

]

# Конфигурация Celery Beat
celery_instance.conf.beat_schedule = {
    "set-expired-tasks-every-5-minutes": {
        "task": "tasks.process_siem_events_task",  # Имя, указанное в @shared_task(name=...)
        "schedule": crontab(minute="*/3")
    },
}
