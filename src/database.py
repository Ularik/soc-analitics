from sqlalchemy import NullPool, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings

# Обычный (синхронный) URL, например: postgresql://user:pass@localhost/dbname
DB_URL = settings.DB_URL_SYNC

# Синхронные движки
engine = create_engine(DB_URL, echo=False)
engine_null_pool = create_engine(DB_URL, poolclass=NullPool)

# Синхронные фабрики сессий
Session = sessionmaker(engine, expire_on_commit=False)
SessionNullPool = sessionmaker(engine_null_pool, expire_on_commit=False)


class Base(DeclarativeBase):
    pass