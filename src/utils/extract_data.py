from src.schemas.detection_events_schemas import EventItem

def _extract_event_item(event_log: dict, attack_name: str, event_hash: str) -> EventItem:
    """Вспомогательная функция для сборки EventItem из лога."""
    # Безопасное получение порта
    d_port = event_log.get("d_port")
    s_port = event_log.get("s_port")

    # Полезная нагрузка (если есть, ограничиваем по длине)
    raw_payload = event_log.get("payload")
    payload_sample = str(raw_payload)[:300] if raw_payload else None

    return EventItem(
        event_hash=event_hash,
        event_time=event_log.get("event_time") or event_log.get("start_time"),
        attack_name=attack_name,
        destination_ip=event_log.get("d_ip"),
        destination_port=int(d_port) if d_port is not None else None,
        source_port=int(s_port) if s_port is not None else None,
        destination_country=event_log.get("d_country"),
        action=event_log.get("block"),
        priority=event_log.get("priority"),
        category=event_log.get("category") or event_log.get("scate_id"),
        payload_sample=payload_sample,
    )