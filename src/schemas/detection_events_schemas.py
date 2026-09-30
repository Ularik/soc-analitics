import json
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging

logger = logging.getLogger(__name__)


# ==========================================================
# PYDANTIC СХЕМЫ
# ==========================================================

class EventItem(BaseModel):
    """Событие внутри корреляционной группы."""
    event_hash: str
    event_time: int | None = None
    attack_name: str

    # Сетевые параметры
    destination_ip: str | None = None
    destination_port: int | None = None
    source_port: int | None = None
    destination_country: str | None = None

    # Действие и категория
    action: str | None = Field(default=None, description="ALLOW, DROP, BLOCK и т.д.")
    priority: str | None = None
    category: str | None = None

    # Контекст атаки
    payload_sample: str | None = Field(default=None, description="Очищенный/обрезанный payload")


class CorrelationGroup(BaseModel):
    """Группа корреляции для передачи в LLM."""
    correlation_hash: str

    # Атрибуты источника (Атакующего)
    source_ip: str | None = None
    source_country: str | None = None
    origin_name: str | None = None

    # Временные рамки и счетчики
    first_event_time: int | None = None
    last_event_time: int | None = None
    count: int = 0

    # Список событий
    events: list[EventItem] = Field(default_factory=[])

class SubDataSchema(BaseModel):
    rule_id: int
    etime: str
    cnt: int
    rulename: str
    credibility: str
    risk: int
    set_id: int
    stime: str
    risk_weight: int
    rule_level: int

    model_config = ConfigDict(from_attributes=True)


class DetectionEventSchema(BaseModel):
    current_level: int
    expired_time: int
    rulename: str
    line_status: str
    type: str
    userid: str
    notice_sound: int
    s_addr: str
    samefield_hash: str
    set_id: int
    inst_id: str
    credibility: int
    rulegroup_id: str
    origin_name: str
    prediction_nm: Optional[str] = None
    method: str
    ruleset: bool
    s_country: str
    d_info: str
    techniques_id: Optional[str] = None
    rulegroup: str
    status: Optional[str] = None
    distance: int
    ruleset_id: Optional[str] = None
    line: str  # Текстовое поле с JSON
    origin: str
    stime: str
    origin_id: int
    sub_data: List[SubDataSchema]
    access_right: str
    s_info: str
    d_country: str
    ruleset_set_id: Optional[int] = None
    incident_hash: str
    hitcount: str  # В сыром JSON передается как строка "{\"count(*)\":23}"
    direction: str
    prediction_cd: Optional[str] = None
    d_addr: str
    s_port: str
    ai_score: Optional[float] = None
    display: int
    cnt: int
    tactics_id: Optional[str] = None
    display_level: int
    d_port: str
    rule_id: int
    max_level: int
    etime: str
    risk: int
    risk_weight: int

    model_config = ConfigDict(from_attributes=True)

    def parse_line(self) -> dict:
        """Вспомогательный метод для безопасного парсинга JSON из поля line."""
        try:
            return json.loads(self.line)
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def s_ip(self) -> Optional[str]:
        """Удобный свойство-геттер для получения s_ip напрямую из line."""
        return self.parse_line().get("s_ip")


class FilteredDetectionEventSchema(BaseModel):
    data: DetectionEventSchema
    event_hash: str

class NoticeListSchema(BaseModel):
    result: List[DetectionEventSchema]

    model_config = ConfigDict(from_attributes=True)


class ResponseDataSchema(BaseModel):
    seeNotice: str | None = None
    noticeList: NoticeListSchema | None = None

    model_config = ConfigDict(from_attributes=True)


class DetectionNoticeResponse(BaseModel):
    data: ResponseDataSchema

    model_config = ConfigDict(from_attributes=True)