from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal
from datetime import datetime
from uuid import UUID

class ReportGenerateSchema(BaseModel):
    origin_name: str = Field(description="Организация")
    source_ip: str = Field(description="Источник угрозы. IP-адресс откуда пришел запрос")
    host: str | None = Field(description="Домен куда направлялся запрос.", default='')
    detection_tool: Literal["WAF", "IPS"] = Field(description="Средство обнаружения: WAF, IPS")
    methods: str = Field(description="Метод атаки (поле method)")
    risk_assessment: Literal["Критическая", "Высокая", "Средняя", "Низкая"] = Field(description="Критичность. Уровень угрозы: критическая, высокая, средняя, низкая")

    country: str = Field(description="Код страны (например, UA, RU, US)")
    detection_date: datetime = Field(description="Дата обнаружения в формате ISO 8601")
    attack_type: str = Field(description="Тип угрозы / Название сигнатуры")
    destination_ip: str = Field(description="IP-адрес назначения")
    cve: str | None = Field(description="Связанный CVE, иначе N/A", default='')

    # Поля с ограниченным объемом текста для защиты от зацикливания:
    protocols_ports: str = Field(description="Протокол и порт (например, TCP/80)")

    potential_impact: str = Field(
        description="Потенциальные последствия для системы в случае успеха атаки (2-3 предложения)"
    )
    data_or_payload: str = Field(
        description="Краткая выжимка/декодированный фрагмент payload (максимум 200 символов, НЕ копируй сырой base64 целиком)"
    )
    short_description: str = Field(
        description="Развернутое описание атаки: вектор, техническая суть уязвимости и маскировка (2-4 предложения)."
    )

    response_actions: str = Field(
        description="Подробный нумерованный список из 4-5 шагов реагирования для SOC: 1. Блокировка... 2. Проверка логов... 3. Изоляция/Патчинг... 4. Ротация ключей..."
    )
    model_config = ConfigDict(from_attributes=True)

    @field_validator("detection_date", mode="after")
    @classmethod
    def make_naive(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            # Преобразуем в UTC и убираем tzinfo
            return v.astimezone().replace(tzinfo=None)
        return v

class ReportCreateSchema(ReportGenerateSchema):
    user_id: int
    file_content: bytes | None = None
    file_name: str | None = None


class ReportDeliverySchema(BaseModel):
    report_id: int
    status: Literal["pending", "success", "error"]
    idempotency_key: UUID
    retry_count: int = 0
    last_error: str | None = None
    sent_at: datetime = datetime.now()
    external_report_id: int | None = None
    updated_at: datetime = datetime.now()

    model_config = ConfigDict(from_attributes=True)


class ReportOutSchema(ReportGenerateSchema):
    origin_name: None = None
    organization_id: int
    file_name: str
    model_config = ConfigDict(from_attributes=True)