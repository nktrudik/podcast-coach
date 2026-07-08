import base64
import os
from collections.abc import Mapping
from typing import cast

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam

from app.clients.errors import ClientValidationError, STTRequestError, STTTimeoutError
from app.clients.retry import run_with_retry
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _extract_retry_after_seconds(exc: RateLimitError) -> int | None:
    """Extract retry-after from the provider response when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None

    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return None

    retry_after_raw = headers.get("retry-after") or headers.get("Retry-After")

    if isinstance(retry_after_raw, str) and retry_after_raw.strip().isdigit():
        retry_after = int(retry_after_raw.strip())
        return retry_after if retry_after > 0 else None

    if isinstance(retry_after_raw, int) and retry_after_raw > 0:
        return retry_after_raw

    return None


def _read_audio_base64(audio_path: str) -> str:
    """Read an audio file and encode it as base64."""
    with open(audio_path, "rb") as file_obj:
        return base64.b64encode(file_obj.read()).decode("utf-8")


def _detect_audio_format(audio_path: str) -> str:
    """Detect audio format from the file extension."""
    ext = os.path.splitext(audio_path)[1].lower().replace(".", "")
    return ext or "wav"


def _validate_audio_path(audio_path: str) -> str:
    """Validate the audio path before sending it to STT."""
    if not isinstance(audio_path, str):
        raise ClientValidationError("Audio path must be a string")

    normalized_path = audio_path.strip()
    if not normalized_path:
        raise ClientValidationError("Audio path must not be empty")
    if not os.path.isfile(normalized_path):
        raise ClientValidationError("Audio file was not found")

    return normalized_path


def _validate_prompt(prompt: str) -> str:
    """Validate the text prompt used for STT."""
    if not isinstance(prompt, str):
        raise ClientValidationError("Prompt must be a string")

    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ClientValidationError("Prompt must not be empty")

    return normalized_prompt


def _extract_text_from_content(content: object) -> str:
    """Extract text from content formats returned by OpenRouter."""
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
    """Send audio to the external STT provider and return a transcript."""
    normalized_path = _validate_audio_path(audio_path)
    normalized_prompt = _validate_prompt(prompt)

    client = OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
    )
    logger.info("Starting audio transcription")

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
            "The STT provider timed out",
            details={
                "timeout_seconds": settings.external_request_timeout_seconds,
                "attempts": settings.stt_request_max_attempts,
            },
        ) from exc
    except APIConnectionError as exc:
        raise STTRequestError(
            "Failed to connect to the STT provider",
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
            "The speech recognition provider is currently rate limited. "
            "Try again in one or two minutes.",
            details=details,
        ) from exc
    except Exception as exc:
        logger.warning("STT request failed: %s", exc)
        raise STTRequestError(
            "Failed to get a transcript from the STT provider",
            details={"attempts": settings.stt_request_max_attempts},
        ) from exc

    try:
        response_message = completion.choices[0].message
    except (AttributeError, IndexError, TypeError) as exc:
        raise STTRequestError("The STT provider returned an invalid response") from exc

    message_content = _extract_text_from_content(response_message.content)
    if not message_content:
        raise STTRequestError("The STT provider returned an empty transcript")

    logger.info("Audio transcription completed successfully")

    return message_content.strip()
