from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.logging_conf.logging_conf import setup_logging
from src.routers.routers import router
from fastapi.middleware.cors import CORSMiddleware
from src.redis.init import redis_manager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await redis_manager.connect()
    FastAPICache.init(RedisBackend(redis_manager.redis), prefix="fastapi-cache")
    yield
    await redis_manager.close()


app = FastAPI(
    title="API Обработчик запросов",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Hello World"}