import base64
import os
from typing import Any, cast

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam

from app.clients.errors import ClientValidationError, STTRequestError, STTTimeoutError
from app.clients.retry import run_with_retry
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _extract_retry_after_seconds(exc: RateLimitError) -> int | None:
    """Пытается извлечь retry-after из ответа провайдера."""
    response = getattr(exc, "response", None)
    if response is None:
        return None

    headers = getattr(response, "headers", None)
    if headers is None:
        return None

    retry_after_raw: Any = None
    if hasattr(headers, "get"):
        retry_after_raw = headers.get("retry-after") or headers.get("Retry-After")

    if isinstance(retry_after_raw, str) and retry_after_raw.strip().isdigit():
        retry_after = int(retry_after_raw.strip())
        return retry_after if retry_after > 0 else None

    if isinstance(retry_after_raw, int) and retry_after_raw > 0:
        return retry_after_raw

    return None


def _read_audio_base64(audio_path: str) -> str:
    """Читает аудиофайл и кодирует его в base64."""
    with open(audio_path, "rb") as file_obj:
        return base64.b64encode(file_obj.read()).decode("utf-8")


def _detect_audio_format(audio_path: str) -> str:
    """Определяет формат аудио по расширению файла."""
    ext = os.path.splitext(audio_path)[1].lower().replace(".", "")
    return ext or "wav"


def _validate_audio_path(audio_path: str) -> str:
    """Проверяет путь до аудио перед отправкой в STT."""
    if not isinstance(audio_path, str):
        raise ClientValidationError("Путь к аудио должен быть строкой")

    normalized_path = audio_path.strip()
    if not normalized_path:
        raise ClientValidationError("Путь к аудио не должен быть пустым")
    if not os.path.isfile(normalized_path):
        raise ClientValidationError("Аудиофайл не найден")

    return normalized_path


def _validate_prompt(prompt: str) -> str:
    """Проверяет текстовый промпт для STT."""
    if not isinstance(prompt, str):
        raise ClientValidationError("Промпт должен быть строкой")

    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ClientValidationError("Промпт не должен быть пустым")

    return normalized_prompt


def _extract_text_from_content(content: Any) -> str:
    """Извлекает текст из разных форматов content, которые может вернуть OpenRouter."""
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
                dict_text = item.get("text")
                if isinstance(dict_text, str) and dict_text.strip():
                    parts.append(dict_text.strip())
                continue

            text_attr = getattr(item, "text", None)
            if isinstance(text_attr, str) and text_attr.strip():
                parts.append(text_attr.strip())

        return "\n".join(parts).strip()

    return ""


def transcribe_audio(
    audio_path: str, prompt: str = "Send transcript in English"
) -> str:
    """Отправляет аудио во внешний STT-сервис и возвращает транскрипт."""
    normalized_path = _validate_audio_path(audio_path)
    normalized_prompt = _validate_prompt(prompt)

    client = OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
    )
    logger.info("Начата транскрибация аудио")

    audio_data = _read_audio_base64(normalized_path)
    audio_format = _detect_audio_format(normalized_path)
    messages = [
        cast(
            ChatCompletionMessageParam,
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": normalized_prompt,
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": audio_format,
                        },
                    },
                ],
            },
        )
    ]

    try:
        completion = run_with_retry(
            operation=lambda: client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
                    "X-OpenRouter-Title": os.getenv("OPENROUTER_SITE_NAME", ""),
                },
                extra_body={},
                model=settings.stt_model_name,
                messages=messages,
                timeout=settings.external_request_timeout_seconds,
            ),
            operation_name="STT",
            max_attempts=settings.stt_request_max_attempts,
            delay_seconds=settings.stt_request_retry_delay_seconds,
            retry_on=(APITimeoutError, APIConnectionError, RateLimitError),
        )
    except APITimeoutError as exc:
        raise STTTimeoutError(
            "Превышено время ожидания ответа STT-сервиса",
            details={
                "timeout_seconds": settings.external_request_timeout_seconds,
                "attempts": settings.stt_request_max_attempts,
            },
        ) from exc
    except APIConnectionError as exc:
        raise STTRequestError(
            "Не удалось подключиться к STT-сервису",
            details={"attempts": settings.stt_request_max_attempts},
        ) from exc
    except RateLimitError as exc:
        retry_after_seconds = _extract_retry_after_seconds(exc)
        details = {
            "attempts": settings.stt_request_max_attempts,
            "provider_status": 429,
        }
        if retry_after_seconds is not None:
            details["retry_after_seconds"] = retry_after_seconds

        raise STTRequestError(
            "Сервис распознавания речи сейчас перегружен (лимит запросов). "
            "Попробуй повторить загрузку через 1-2 минуты.",
            details=details,
        ) from exc
    except Exception as exc:
        logger.warning("Ошибка обращения к STT: %s", exc)
        raise STTRequestError(
            "Не удалось получить транскрипт от STT-сервиса",
            details={"attempts": settings.stt_request_max_attempts},
        ) from exc

    try:
        response_message = completion.choices[0].message
    except (AttributeError, IndexError, TypeError) as exc:
        raise STTRequestError("STT-сервис вернул некорректный ответ") from exc

    message_content = _extract_text_from_content(response_message.content)
    if not message_content:
        raise STTRequestError("STT-сервис вернул пустой транскрипт")

    logger.info("Транскрибация успешно завершена")

    return message_content.strip()
