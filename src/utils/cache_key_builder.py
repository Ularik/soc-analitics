from typing import Optional
import hashlib

def custom_log_key_builder(
        content: str,
        namespace: Optional[str] = "",
) -> str:
    if isinstance(content, dict):
        content = str(content)

    # Нормализуем строку (удаляем непечатные символы и пробелы по краям)
    cleaned_body = "".join(char for char in content if ord(char) >= 32).strip()
    # Хешируем строку для компактного ключа в Redis
    body_hash = hashlib.md5(cleaned_body.encode("utf-8")).hexdigest()

    return f"{namespace}:gemini_log:{body_hash}"