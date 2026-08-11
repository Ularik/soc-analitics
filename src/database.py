from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import settings

DB_URL = settings.DB_URL
engine = create_async_engine(settings.DB_URL, echo=False)  # по умолчанию держит 15 соединений

AsyncSession = async_sessionmaker(
    engine, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass