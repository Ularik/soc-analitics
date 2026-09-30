from typing import Annotated
from fastapi import Depends, Request, HTTPException
from src.database import Session
from src.db_manager.db_manager import DbManager
from src.rabbitmq.init import rabbit_client, RabbitClient


def get_db():
    with DbManager(session_factory=Session) as db:
        yield db


DBDep = Annotated[DbManager, Depends(get_db)]


def get_token(request: Request) -> str:
    token = request.cookies.get("access_token", None)
    if not token:
        raise HTTPException(status_code=401, detail="Вы не передали токен аутентификации")
    return token


def get_rmq_channel():
    with rabbit_client as channel:
        yield channel


RMQDep = Annotated[RabbitClient, Depends(get_rmq_channel)]