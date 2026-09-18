from celery import shared_task
from src.redis.sync_redis import redis_incident_manager
from src.tasks.beat_tasks import analyze_attack_task
from src.tasks.telegram_tasks import send_telegram_attack_task
import logging


logger = logging.getLogger(__name__)


@shared_task(
    name="src.tasks.attack_tasks.finalize_attack_group"
)
def finalize_attack_group(
    correlation_hash: str
):

    group = redis_incident_manager.get_correlation_group(
        correlation_hash
    )

    if group is None:
        logger.info(
            f"Группа уже обработана: "
            f"{correlation_hash}"
        )
        return

    logger.warning(
        f"Завершаем группу {correlation_hash}: "
        f"{group['count']} событий"
    )

    try:

        analyze_attack_task.delay(
            attack_group=group
        )

        send_telegram_attack_task.delay(
            attack_group=group
        )

    except Exception as e:

        logger.exception(
            f"Ошибка обработки группы "
            f"{correlation_hash}: {e}"
        )

        return

    redis_incident_manager.delete_correlation_group(
        correlation_hash
    )