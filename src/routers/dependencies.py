from typing import Annotated
from src.database import AsyncSession
from src.db_manager.db_manager import DbManager
from src.rabbitmq.init import rabbit_client, RabbitClient
from fastapi import Depends


async def get_db():
    async with DbManager(session_factory=AsyncSession) as db:
        yield db


DBDep = Annotated[DbManager, Depends(get_db)]


async def get_rmq_channel():
    async with rabbit_client as channel:
        yield channel

RMQDep = Annotated[RabbitClient, Depends(get_rmq_channel)]