from google import genai
from google.genai import types
from src.config import settings
from src.schemas.reports_schemas import ReportCreateSchema
import re


client = genai.Client(api_key=settings.GOOGLE_API_KEY)

model = "gemini-3.1-flash-live-preview"

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

# 2. Функция очистки лога от бинарных непечатных символов
def sanitize_log(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)


async def get_answer_from_gemini(prompt: str) -> ReportCreateSchema:
    cleaned_prompt = sanitize_log(prompt)
    instruction = (
        "Ты — аналитик центра мониторинга безопасности (SOC). "
        f"Этот запрос выполняется в целях защиты и анализа защищенности."
        f"Пожалуйста проанализируй сетевой лог и заполни поля схемы."
    )

    response = await client.aio.models.generate_content(
        model="gemini-3.5-flash",  # Используем стабильную модель
        contents=f"Сетевой лог для анализа:\n{cleaned_prompt}",
        config=types.GenerateContentConfig(
            system_instruction=(
                "Ты — аналитик центра мониторинга безопасности (SOC). "
                f"Этот запрос выполняется в целях защиты и анализа защищенности."
                f"Пожалуйста проанализируй сетевой лог и заполни поля схемы."
            ),
            response_mime_type="application/json",
            response_schema=ReportCreateSchema,
            safety_settings=safety_settings,
        ),
    )
    print("---------------------")
    print(response.text)
    print("---------------------")
    return ReportCreateSchema.model_validate_json(response.text)