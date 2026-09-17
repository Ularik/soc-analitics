import logging
from datetime import datetime
from pydantic import ValidationError
import requests
import urllib3
from src.config import settings
from src.schemas.detection_events_schemas import DetectionNoticeResponse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class SiemSessionManager:
    BASE_URL = settings.SIEM_URL
    USERNAME = settings.SIEM_LOGIN
    PASSWORD = settings.SIEM_PASSWORD

    LOGIN_URL = f"{BASE_URL}/siem/j_spring_security_check"
    EVENTS_URL = f"{BASE_URL}/siem/common/get_footer_value.do"
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def __init__(self):
        self.session: requests.Session | None = None

    def _init_session(self):
        """Создает сессию и проходит авторизацию."""
        logger.info("Инициализация новой сессии в SIEM...")
        session = requests.Session()
        session.verify = False
        session.headers.update(self.HEADERS)

        login_payload = {"j_username": self.USERNAME, "j_password": self.PASSWORD}
        try:
            res = session.post(self.LOGIN_URL, data=login_payload, timeout=10)
            if "j_spring_security_check" in res.text or "Please enter ID" in res.text:
                raise requests.AuthenticationError("Неверный логин или пароль в SIEM")

            self.session = session
            logger.info("Успешная авторизация в SIEM.")
        except Exception as e:
            session.close()
            self.session = None
            raise e

    @property
    def get_payload(self) -> dict:
        return {
            "footerNoticeTime": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "alarmType": "topN",
        }

    def _relogin_and_retry(self) -> DetectionNoticeResponse:
        """Вспомогательный метод для сброса сессии и повторного запроса."""
        logger.warning("Данные неполные или сессия протухла. Выполняем повторный вход...")
        if self.session:
            self.session.close()
        self._init_session()

        res = self.session.post(self.EVENTS_URL, data=self.get_payload, timeout=10)
        res.raise_for_status()
        return DetectionNoticeResponse.model_validate(res.json())

    def fetch_events(self) -> DetectionNoticeResponse:
        """Получает события. Если сессии нет, она просрочена или пришел пустой ответ — переавторизуется."""
        if not self.session:
            self._init_session()

        try:
            res = self.session.post(self.EVENTS_URL, data=self.get_payload, timeout=10)

            # 1. Проверка на явный редирект на HTML-страницу логина
            if "j_spring_security_check" in res.text or "Please enter ID" in res.text:
                return self._relogin_and_retry()

            res.raise_for_status()
            result = DetectionNoticeResponse.model_validate(res.json())

            # 2. Проверяем валидность полученных Optional полей
            data = result.data
            if data is None or data.seeNotice is None or data.noticeList is None:
                logger.warning(
                    "В ответе SIEM отсутствуют обязательные поля (seeNotice/noticeList). Повторная авторизация...")
                result = self._relogin_and_retry()

            return result

        except (ValidationError, requests.RequestException) as e:
            logger.error(f"Ошибка при запросе или парсинге ответа SIEM: {e}")
            if self.session:
                self.session.close()
                self.session = None
            raise e


# Синглтон клиента — создается при загрузке Celery Worker
siem_client = SiemSessionManager()