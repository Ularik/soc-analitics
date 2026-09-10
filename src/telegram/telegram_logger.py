import logging
import requests
from src.config import settings
from src.schemas.reports_schemas import ReportGenerateSchema


logger = logging.getLogger(__name__)


class TelegramLogger:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

        self.url = (
            f"https://api.telegram.org/bot"
            f"{self.bot_token}/sendMessage"
        )

    def send(self, message: str) -> bool:
        """
        Отправляет сообщение в Telegram.

        Возвращает:
            True  - сообщение отправлено
            False - произошла ошибка
        """

        if not self.bot_token or not self.chat_id:
            logger.error("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены")
            return False

        try:
            response = requests.post(
                self.url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )

            response.raise_for_status()

            logger.info("Сообщение успешно отправлено в Telegram")
            return True

        except requests.exceptions.HTTPError as e:
            # Извлекаем ответ от самого Telegram API
            error_details = (
                response.text if "response" in locals() else "Нет ответа от сервера"
            )
            logger.error(
                f"HTTP ошибка от Telegram API [{response.status_code}]: {error_details}"
            )
            return False

        except requests.RequestException as e:
            # Ошибки сети, таймауты, проблемы с DNS
            logger.error(f"Сетевая ошибка при отправке в Telegram: {e}")
            return False

    def send_attack(self, *, status: str, ip: str, rule_name: str | None = None, node: str | None = None,
                    attempts: int | str | None = None, ) -> bool:
        message = (
            "🚨 <b>ОБНАРУЖЕНА ВНЕШНЯЯ АТАКА</b>\n\n" 
            f"<b>Статус:</b> {status}\n" 
            f"<b>IP:</b> <code>{ip}</code>\n" 
            f"<b>Правило:</b> {rule_name or 'Не указано'}\n" 
            f"<b>Узел:</b> {node or 'Не указан'}\n" 
            f"<b>Попыток:</b> {attempts or 0}")

        return self.send(message)

    def send_analysis(self, report: ReportGenerateSchema) -> bool:
        message = (
            "🤖 <b>АНАЛИЗ ИНЦИДЕНТА</b>\n\n"

            f"🏢 <b>Организация:</b> "
            f"{str(report.origin_name)}\n"

            f"🌍 <b>Страна:</b> "
            f"{str(report.country)}\n"

            f"🚨 <b>Уровень риска:</b> "
            f"{str(report.risk_assessment)}\n\n"

            f"🎯 <b>Тип атаки:</b> "
            f"{str(report.attack_type)}\n"

            f"🛡 <b>Инструмент обнаружения:</b> "
            f"{(str(report.detection_tool))}\n"

            f"📡 <b>Метод:</b> "
            f"{(str(report.methods))}\n"

            f"🌐 <b>Источник:</b> "
            f"<code>{(str(report.source_ip))}</code>\n"

            f"🎯 <b>Назначение:</b> "
            f"<code>{(str(report.destination_ip))}</code>\n"

            f"🖥 <b>Host:</b> "
            f"{(str(report.host))}\n"

            f"🔌 <b>Протокол/порт:</b> "
            f"{(str(report.protocols_ports))}\n"

            f"📅 <b>Дата:</b> "
            f"{(str(report.detection_date))}\n"

            f"🔐 <b>CVE:</b> "
            f"{(str(report.cve))}\n\n"

            "📋 <b>Описание атаки</b>\n"
            f"{(str(report.short_description))}\n\n"

            "💥 <b>Потенциальное воздействие</b>\n"
            f"{(str(report.potential_impact))}\n\n"

            "📦 <b>Payload</b>\n"
            f"<code>{(str(report.data_or_payload))}</code>\n\n"

            "🛡 <b>Рекомендации по реагированию</b>\n"
            f"{(str(report.response_actions))}"
        )

        return self.send(message)


telegram_logger = TelegramLogger()

