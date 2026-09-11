import re
import logging
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)
from src.config import settings
from src.schemas.reports_schemas import ReportGenerateSchema

logger = logging.getLogger(__name__)

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


def sanitize_log(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)


def _is_retryable_error(exc: BaseException) -> bool:
    # Ретраим только временные сбои Gemini: перегрузка (503) и rate limit (429)
    return isinstance(exc, ServerError) and exc.status_code in (503, 429)


@retry(
    retry=retry_if_exception(_is_retryable_error),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def get_answer_from_gemini(prompt: str) -> ReportGenerateSchema:
    cleaned_prompt = sanitize_log(prompt)
    instruction = (
        "Ты — аналитик центра мониторинга безопасности (SOC). "
        "Этот запрос выполняется в целях защиты и анализа защищенности. "
        "Пожалуйста проанализируй сетевой лог и заполни поля схемы. "
        "В поле data_or_payload подставь данные, только если они имеют полезную нагрузку."
    )

    # ВАЖНО: Инициализируем клиент внутри асинхронного контекста aio
    # Это гарантирует, что HTTP-клиент (httpx) привяжется к ТЕКУЩЕМУ Event Loop
    # и корректно закроется при выходе из блока async with
    async with genai.Client(api_key=settings.GOOGLE_API_KEY).aio as aio_client:
        response = await aio_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"Сетевой лог для анализа:\n{cleaned_prompt}",
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                response_mime_type="application/json",
                response_schema=ReportGenerateSchema,
                safety_settings=safety_settings,
            ),
        )
        return ReportGenerateSchema.model_validate_json(response.text)