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
            logger.error(
                "TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены"
            )
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

        except requests.RequestException:
            logger.exception(
                "Ошибка при отправке сообщения в Telegram"
            )
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
            f"{str(report.get('origin_name', 'N/A'))}\n"

            f"🌍 <b>Страна:</b> "
            f"{str(report.get('country', 'N/A'))}\n"

            f"🚨 <b>Уровень риска:</b> "
            f"{str(report.get('risk_assessment', 'N/A'))}\n\n"

            f"🎯 <b>Тип атаки:</b> "
            f"{str(report.get('attack_type', 'N/A'))}\n"

            f"🛡 <b>Инструмент обнаружения:</b> "
            f"{(str(report.get('detection_tool', 'N/A')))}\n"

            f"📡 <b>Метод:</b> "
            f"{(str(report.get('methods', 'N/A')))}\n"

            f"🌐 <b>Источник:</b> "
            f"<code>{(str(report.get('source_ip', 'N/A')))}</code>\n"

            f"🎯 <b>Назначение:</b> "
            f"<code>{(str(report.get('destination_ip', 'N/A')))}</code>\n"

            f"🖥 <b>Host:</b> "
            f"{(str(report.get('host') or 'N/A'))}\n"

            f"🔌 <b>Протокол/порт:</b> "
            f"{(str(report.get('protocols_ports', 'N/A')))}\n"

            f"📅 <b>Дата:</b> "
            f"{(str(report.get('detection_date', 'N/A')))}\n"

            f"🔐 <b>CVE:</b> "
            f"{(str(report.get('cve') or 'N/A'))}\n\n"

            "📋 <b>Описание атаки</b>\n"
            f"{(str(report.get('short_description', 'N/A')))}\n\n"

            "💥 <b>Потенциальное воздействие</b>\n"
            f"{(str(report.get('potential_impact', 'N/A')))}\n\n"

            "📦 <b>Payload</b>\n"
            f"<code>{(str(report.get('data_or_payload', 'N/A')))}</code>\n\n"

            "🛡 <b>Рекомендации по реагированию</b>\n"
            f"{(str(report.get('response_actions', 'N/A')))}"
        )

        return self.send(message)


telegram_logger = TelegramLogger()
