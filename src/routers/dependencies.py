from typing import Annotated
from src.database import AsyncSession
from src.db_manager.db_manager import DbManager
from fastapi import Depends


async def get_db():
    async with DbManager(session_factory=AsyncSession) as db:
        yield db


DBDep = Annotated[DbManager, Depends(get_db)]
