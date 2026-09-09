from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# 1. Регистрация шрифта (с фолбэком для разных ОС)
try:
    pdfmetrics.registerFont(TTFont('TimesNewRoman', r'/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'))
except Exception:
    pdfmetrics.registerFont(TTFont('TimesNewRoman', r'C:\Windows\Fonts\times.ttf'))

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
    REDIS_HOST_DOCKER: str
    REDIS_PORT: str

    RMQ_USER: str
    RMQ_PASSWORD: str
    RMQ_HOST: str
    RMQ_HOST_DOCKER: str
    RMQ_PORT: int

    CERT_GOV: str

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str

    @property
    def DB_URL(self):
        host = [self.POSTGRES_HOST, self.POSTGRES_HOST_DOCKER][self.MODE == "DOCKER"]
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self):
        host = [self.REDIS_HOST, self.REDIS_HOST_DOCKER][self.MODE == "DOCKER"]
        return f"redis://{host}:{self.REDIS_PORT}"

    @property
    def RMQ_URL(self):
        host = [self.RMQ_HOST, self.RMQ_HOST_DOCKER][self.MODE == "DOCKER"]
        return f"amqp://{self.RMQ_USER}:{self.RMQ_PASSWORD}@{host}/"

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

settings = Settings()