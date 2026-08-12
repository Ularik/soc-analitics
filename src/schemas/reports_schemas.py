from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal
from datetime import datetime
from uuid import UUID

class ReportGenerateSchema(BaseModel):
    country: str = Field(description="Код страны")
    detection_date: datetime = Field(description="Дата обнаружения")
    origin_name: str = Field(description="Организация")
    attack_type: str = Field(description="Тип угрозы")
    source_ip: str = Field(description="Источник угрозы. IP-адресс откуда пришел запрос")
    destination_ip: str = Field(description="IP-адресс куда адрессовался запрос")
    host: str | None = Field(description="Домен куда направлялся запрос.", default='')
    cve: str | None = Field(description="CVE", default='')
    detection_tool: Literal["WAF", "IPS"] = Field(description="Средство обнаружения: WAF, IPS")
    short_description: str = Field(description="Краткое описание")
    methods: str = Field(description="Метод атаки")
    protocols_ports: str = Field(description="Протоколы и порты адресата")
    risk_assessment: Literal["Критическая", "Высокая", "Средняя", "Низкая"] = Field(description="Критичность. Уровень угрозы: критическая, высокая, средняя, низкая")
    potential_impact: str = Field(description="Потенциальные последствия")
    data_or_payload: str = Field(description="Данные из тела запроса или payload")
    response_actions: str = Field(description="Методы для защиты")

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