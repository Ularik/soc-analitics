from contextlib import asynccontextmanager  # 1. Меняем импорт
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from src.exceptions.exception_handlers import register_exception_handlers
from src.logging_conf.logging_conf import setup_logging
from src.rabbitmq.init import rabbit_client
from src.redis.init import redis_manager
from src.routers.reports import router as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    redis_manager.connect()
    rabbit_client.connect()

    # Инициализация fastapi-cache
    FastAPICache.init(RedisBackend(redis_manager.client), prefix="fastapi-cache")

    yield

    # Синхронное закрытие ресурсов
    redis_manager.close()
    rabbit_client.close()  # Также рекомендуется закрыть соединение с RabbitMQ


app = FastAPI(
    title="API Обработчик запросов",
    lifespan=lifespan
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router)
