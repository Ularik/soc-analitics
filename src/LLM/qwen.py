import re
import httpx
from fastapi import HTTPException
from src.schemas.reports_schemas import ReportGenerateSchema

url = "http://localhost:1234/v1"


def sanitize_log(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)


# Формируем компактный образец JSON один раз при старте приложения
PROMPT_SCHEMA_TEMPLATE = ReportGenerateSchema.model_json_schema()


async def get_answer_from_qwen(prompt: str) -> ReportGenerateSchema:
    cleaned_prompt = sanitize_log(prompt)

    SYSTEM_PROMPT = """Ты — SOC-аналитик L2. Проанализируй входящий лог безопасности и заполни структуру JSON.

    Правила заполнения:
    1. В поле `data_or_payload` выделяй ТОЛЬКО ключевую вредоносную часть (URI, заголовки, декодированные строки). Запрещено вставлять длинные бинарные/Base64 дампы.
    2. В поле `short_description`: подробно опиши суть атаки с разъяснением уязвимости и её сущности и действиями злоумышленников.
    3. В поле `response_actions`: составь пошаговый и развернутый Playbook по реагированию (минимум 3-5 шагов). Включай первичные действия по блокировке, шаги по содержанию инцидента (containment), проверке смежных логов и рекомендации по ротации учётных данных/патчингу.
    4. В поле `potential_impact` Потенциальные последствия для системы в случае успеха атаки (2-3 предложения).
    """

    payload = {
        "model": "darkidol-llama-3.1-8b", # "qwen",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Лог:\n{cleaned_prompt}"}
        ],
        "temperature": 0.1,
        "repetition_penalty": 1.1,
        "max_tokens": 1500,
        # Нативная передача схемы через response_format
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "report_generate_schema",
                "strict": True,
                "schema": ReportGenerateSchema.model_json_schema()
            }
        }

    }

    async with httpx.AsyncClient(base_url=url, timeout=300.0) as client:
        response = await client.post("/chat/completions", json=payload)

        if response.is_error:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка локальной LLM ({response.status_code}): {response.text}"
            )

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # При использовании response_format markdown-обертки ```json не создаются
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?|```$", "", content, flags=re.MULTILINE).strip()

    return ReportGenerateSchema.model_validate_json(content)