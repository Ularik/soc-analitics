import logging
from datetime import datetime
from pprint import pprint

import requests
import urllib3
from src.schemas.detection_events_schemas import DetectionNoticeResponse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class SiemSessionManager:
    BASE_URL = "https://192.168.30.101:10443"
    USERNAME = "igloosec"
    PASSWORD = "Sp!dertm70"

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

    def fetch_events(self) -> DetectionNoticeResponse:
        """Получает события. Если сессии нет или она просрочена — переавторизуется."""
        if not self.session:
            self._init_session()

        try:
            res = self.session.post(self.EVENTS_URL, data=self.get_payload, timeout=10)

            # Проверяем, не редиректнуло ли нас на страницу логина из-за таймаута
            if "j_spring_security_check" in res.text or "Please enter ID" in res.text:
                logger.warning("Сессия SIEM истекла. Выполняем повторный вход...")
                self._init_session()
                res = self.session.post(self.EVENTS_URL, data=self.get_payload, timeout=10)

            res.raise_for_status()
            return DetectionNoticeResponse.model_validate(res.json())

        except (requests.RequestException, requests.HTTPError) as e:
            logger.error(f"Ошибка при запросе к SIEM: {e}")
            # Сбрасываем сессию, чтобы при следующем запуске прошла чистая авторизация
            if self.session:
                self.session.close()
                self.session = None
            raise e


# Синглтон клиента — создается при загрузке Celery Worker
siem_client = SiemSessionManager()