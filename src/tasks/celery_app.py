from celery import Celery
from celery.schedules import crontab
from src.config import settings

celery_instance = Celery(
    "tasks",
    broker=settings.RMQ_URL,
    backend=f"rpc://",
)

celery_instance.conf.include = [
    "src.tasks.beat_tasks",
]

# Конфигурация Celery Beat
celery_instance.conf.beat_schedule = {
    "set-expired-tasks-every-5-minutes": {
        "task": "src.tasks.beat_tasks.process_siem_events_task",  # Имя, указанное в @shared_task(name=...)
        "schedule": crontab(minute="*/3")
    },
}

celery_instance.conf.update(
    timezone="Asia/Bishkek",
    enable_utc=True,
    # Рекомендуемые базовые настройки для работы с RabbitMQ:
    task_acks_late=True,  # Забирать задачу из очереди только после успешного выполнения
    task_reject_on_worker_lost=True,  # Возвращать задачу в очередь, если воркер "упал"
)