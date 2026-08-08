from src.service.base import BaseService
from src.utils.cache_key_builder import custom_log_key_builder
from src.schemas.reports_schemas import ReportCreateSchema
from src.redis.init import redis_manager
from src.gemini.init import get_answer_from_gemini
from src.db_manager.db_manager import DbManager
from src.database import AsyncSession


class ReportsService(BaseService):

    async def get_answer_from_ai(self, body: str) -> ReportCreateSchema:
        key = custom_log_key_builder(body)
        cached_body = await redis_manager.get(key)

        if cached_body is not None:
            return ReportCreateSchema.model_validate_json(cached_body)

        answer = await get_answer_from_gemini(body)

        await redis_manager.set(key, answer.model_dump_json(), expire=20)
        return answer

    async def create_report(self, body: ReportCreateSchema):   # добавить rabbitmq
        async with DbManager(AsyncSession) as db:
