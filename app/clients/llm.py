from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI

from app.clients.errors import (
    ClientValidationError,
    LLMRequestError,
    LLMTimeoutError,
)
from app.clients.retry import run_with_retry
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _create_client() -> OpenAI:
    """Создает клиент для обращения к языковой модели."""
    return OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
    )


def _to_memory_message(message: Any) -> dict[str, Any]:
    """Приводит ответ модели к формату сообщений истории."""
    return {
        "role": "assistant",
        "content": message.content,
    }


def _extract_text_from_content(content: Any) -> str:
    """Извлекает текст из разных форматов content, которые возвращает OpenRouter."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
                continue

            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
                continue

            text_attr = getattr(item, "text", None)
            if isinstance(text_attr, str) and text_attr.strip():
                parts.append(text_attr.strip())

        return "\n".join(parts).strip()

    return ""


def _validate_text(value: str, field_name: str) -> str:
    """Проверяет, что текстовое поле непустое."""
    if not isinstance(value, str):
        raise ClientValidationError(f"Поле {field_name} должно быть строкой")

    normalized_value = value.strip()
    if not normalized_value:
        raise ClientValidationError(f"Поле {field_name} не должно быть пустым")
    return normalized_value


def _validate_memory(memory: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Проверяет историю сообщений перед отправкой в LLM."""
    if memory is None:
        return []
    if not isinstance(memory, list):
        raise ClientValidationError("Параметр memory должен быть списком")

    validated_memory: list[dict[str, Any]] = []
    for index, item in enumerate(memory):
        if not isinstance(item, dict):
            raise ClientValidationError(f"Элемент memory[{index}] должен быть объектом")
        role = item.get("role")
        content = item.get("content")
        validated_memory.append(
            {
                "role": _validate_text(role, f"memory[{index}].role"),
                "content": _validate_text(content, f"memory[{index}].content"),
            }
        )

    return validated_memory


def ask_llm(
    system_prompt: str,
    message: str,
    memory: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Отправляет запрос в LLM и возвращает ответ вместе с обновленной историей."""
    validated_system_prompt = _validate_text(system_prompt, "system_prompt")
    validated_message = _validate_text(message, "message")
    validated_memory = _validate_memory(memory)

    client = _create_client()
    logger.info("Отправка запроса в LLM")

    user_message = {
        "role": "user",
        "content": validated_message,
    }
    messages = [
        {
            "role": "system",
            "content": validated_system_prompt,
        },
        *validated_memory,
        user_message,
    ]

    try:
        completion = run_with_retry(
            operation=lambda: client.chat.completions.create(
                extra_body={"reasoning": {"enabled": True}},
                model=settings.llm_model_name,
                messages=messages,
                timeout=settings.external_request_timeout_seconds,
            ),
            operation_name="LLM",
            max_attempts=settings.external_request_max_attempts,
            delay_seconds=settings.external_request_retry_delay_seconds,
            retry_on=(APITimeoutError, APIConnectionError),
        )
    except APITimeoutError as exc:
        raise LLMTimeoutError(
            "Превышено время ожидания ответа LLM-сервиса",
            details={
                "timeout_seconds": settings.external_request_timeout_seconds,
                "attempts": settings.external_request_max_attempts,
            },
        ) from exc
    except APIConnectionError as exc:
        raise LLMRequestError(
            "Не удалось подключиться к LLM-сервису",
            details={"attempts": settings.external_request_max_attempts},
        ) from exc
    except Exception as exc:
        logger.warning("Ошибка обращения к LLM: %s", exc)
        raise LLMRequestError(
            "Не удалось получить ответ от языковой модели",
            details={"attempts": settings.external_request_max_attempts},
        ) from exc

    try:
        assistant_response = completion.choices[0].message
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMRequestError("Языковая модель вернула некорректный ответ") from exc

    response_content = _extract_text_from_content(assistant_response.content)
    if not response_content:
        logger.warning(
            "LLM вернула пустой content, тип=%s",
            type(assistant_response.content).__name__,
        )
        raise LLMRequestError("Языковая модель вернула пустой ответ")

    assistant_message = _to_memory_message(assistant_response)
    logger.info("Ответ от LLM успешно получен")

    return response_content, [*validated_memory, user_message, assistant_message]
