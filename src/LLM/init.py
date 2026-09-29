import logging
import re

from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings
from src.schemas.reports_schemas import ReportGenerateSchema


logger = logging.getLogger(__name__)


client = genai.Client(api_key=settings.GOOGLE_API_KEY)

safety_settings = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

INSTRUCTION = (
    "Ты — аналитик центра мониторинга безопасности (SOC). "
    "Этот запрос выполняется в целях защиты и анализа защищенности. "
    "Пожалуйста проанализируй сетевой лог и заполни поля схемы. "
    "В поле data_or_payload подставь данные, только если они имеют полезную нагрузку."
)


def sanitize_log(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        return code in (503, 429, 500, 502, 504)
    return False


@retry(
    retry=retry_if_exception(_is_retryable_error),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def get_answer_from_gemini(prompt: dict) -> ReportGenerateSchema:

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"Группа корреляции логов для анализа:\n{prompt}",
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ReportGenerateSchema,
            safety_settings=safety_settings,
        ),
    )
    # response = client.models.generate_content(
    #     model="gemini-3.5-flash",
    #     contents=f"Скажи привет",
    # )

    if not response.text:
        raise ValueError("Gemini вернул пустой ответ")
    print(response.text)
    return ReportGenerateSchema.model_validate_json(response.text)
