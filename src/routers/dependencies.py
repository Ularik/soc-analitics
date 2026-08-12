from typing import Annotated
from src.database import AsyncSession
from src.db_manager.db_manager import DbManager
from src.rabbitmq.init import rabbit_client, RabbitClient
from fastapi import Depends, Request, HTTPException
from src.service.auth import AuthService


async def get_db():
    async with DbManager(session_factory=AsyncSession) as db:
        yield db


DBDep = Annotated[DbManager, Depends(get_db)]


def get_token(request: Request) -> str:
    token = request.cookies.get("access_token", None)
    if not token:
        raise HTTPException(status_code=401, detail="Вы не передали токен аутентификации")
    return token


async def get_current_user_id(token: str = Depends(get_token)) -> str:
    user_data = await AuthService.encode_token(token)
    return user_data["user_id"]


AuthUserDep = Annotated[int, Depends(get_current_user_id)]


async def get_rmq_channel():
    async with rabbit_client as channel:
        yield channel

RMQDep = Annotated[RabbitClient, Depends(get_rmq_channel)]