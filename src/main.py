from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.logging_conf.logging_conf import setup_logging
from src.routers.reports import router as reports_router
from src.routers.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware
from src.redis.init import redis_manager
from src.rabbitmq.init import rabbit_client
from src.exceptions.exception_handlers import register_exception_handlers
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend



@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await redis_manager.connect()
    await rabbit_client.connect()
    FastAPICache.init(RedisBackend(redis_manager.redis), prefix="fastapi-cache")
    yield
    await redis_manager.close()


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
app.include_router(users_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}