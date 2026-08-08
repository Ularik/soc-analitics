from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    MODE: Literal["LOCAL", "DOCKER", "PROD"]

    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_HOST_DOCKER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: str

    GOOGLE_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: str

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

settings = Settings()