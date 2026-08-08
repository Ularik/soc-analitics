from typing import Annotated
from src.database import async_session_maker
from src.db_manager.db_manager import DbManager
from fastapi import Depends


async def get_db():
    async with DbManager(session_factory=async_session_maker) as db:
        yield db


DBDep = Annotated[DbManager, Depends(get_db)]
