from fastapi import APIRouter, Body, Request, Response
from src.gemini.init import get_answer_from_gemini
from fastapi_cache.decorator import cache, FastAPICache
import hashlib
from typing import Callable, Optional

router = APIRouter()


def custom_log_key_builder(
        func: Callable,
        namespace: Optional[str] = "",
        request: Request = None,
        response: Response = None,
        *args,
        **kwargs,
) -> str:
    # Извлекаем тело запроса ('body')
    raw_body = kwargs.get("body", "")
    if isinstance(raw_body, dict):
        raw_body = str(raw_body)

    # Нормализуем строку (удаляем непечатные символы и пробелы по краям)
    cleaned_body = "".join(char for char in raw_body if ord(char) >= 32).strip()

    # Хешируем строку для компактного ключа в Redis
    body_hash = hashlib.md5(cleaned_body.encode("utf-8")).hexdigest()

    return f"{namespace}:gemini_log:{body_hash}"

@router.post("/get-ai-answer/")
@cache(expire=3600, key_builder=custom_log_key_builder)
async def get_answer_for_log(request: Request, body = Body(embed=True)):
    answer = await get_answer_from_gemini(body)
    return {"result": answer}


