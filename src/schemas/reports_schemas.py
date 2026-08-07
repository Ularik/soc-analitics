from pydantic import BaseModel, Field
from typing import Literal

class ReportCreateSchema(BaseModel):
    detection_date: str = Field(description="Дата обнаружения")
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
