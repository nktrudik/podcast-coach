from collections.abc import Mapping, Sequence

from openai import APIConnectionError, APITimeoutError, OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.clients.errors import (
    ClientValidationError,
    LLMRequestError,
    LLMTimeoutError,
)
from app.clients.retry import run_with_retry
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)
type MemoryMessage = dict[str, str]
_ALLOWED_MEMORY_ROLES = {"user", "assistant", "system"}


def _create_client() -> OpenAI:
    """Create a client for the configured language model provider."""
    return OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
    )


def _to_memory_message(content: str) -> MemoryMessage:
    """Convert model output into a history message."""
    return {
        "role": "assistant",
        "content": content,
    }


def _to_chat_message(message: MemoryMessage) -> ChatCompletionMessageParam:
    """Convert a history message to the typed OpenAI payload."""
    content = message["content"]
    role = message["role"]
    if role == "system":
        return {"role": "system", "content": content}
    if role == "assistant":
        return {"role": "assistant", "content": content}
    return {"role": "user", "content": content}


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


def _validate_text(value: object, field_name: str) -> str:
    """Validate that a value is a non-empty string."""
    if not isinstance(value, str):
        raise ClientValidationError(f"Field {field_name} must be a string")

    normalized_value = value.strip()
    if not normalized_value:
        raise ClientValidationError(f"Field {field_name} must not be empty")
    return normalized_value


def _validate_memory(
    memory: Sequence[Mapping[str, object]] | None,
) -> list[MemoryMessage]:
    """Validate message history before sending it to the LLM."""
    if memory is None:
        return []

    validated_memory: list[MemoryMessage] = []
    for index, item in enumerate(memory):
        role = _validate_text(item.get("role"), f"memory[{index}].role").lower()
        if role not in _ALLOWED_MEMORY_ROLES:
            raise ClientValidationError(
                f"Field memory[{index}].role must be user, assistant, or system"
            )

        validated_memory.append(
            {
                "role": role,
                "content": _validate_text(
                    item.get("content"), f"memory[{index}].content"
                ),
            }
        )

    return validated_memory


def ask_llm(
    system_prompt: str,
    message: str,
    memory: Sequence[Mapping[str, object]] | None = None,
) -> tuple[str, list[MemoryMessage]]:
    """Send a request to the LLM and return the answer plus updated history."""
    validated_system_prompt = _validate_text(system_prompt, "system_prompt")
    validated_message = _validate_text(message, "message")
    validated_memory = _validate_memory(memory)

    client = _create_client()
    logger.info("Sending request to LLM")

    user_message: MemoryMessage = {
        "role": "user",
        "content": validated_message,
    }
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": validated_system_prompt,
        },
        *[_to_chat_message(item) for item in validated_memory],
        _to_chat_message(user_message),
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
            "The LLM provider timed out",
            details={
                "timeout_seconds": settings.external_request_timeout_seconds,
                "attempts": settings.external_request_max_attempts,
            },
        ) from exc
    except APIConnectionError as exc:
        raise LLMRequestError(
            "Failed to connect to the LLM provider",
            details={"attempts": settings.external_request_max_attempts},
        ) from exc
    except Exception as exc:
        logger.warning("LLM request failed: %s", exc)
        raise LLMRequestError(
            "Failed to get a response from the language model",
            details={"attempts": settings.external_request_max_attempts},
        ) from exc

    try:
        assistant_response = completion.choices[0].message
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMRequestError(
            "The language model returned an invalid response"
        ) from exc

    response_content = _extract_text_from_content(assistant_response.content)
    if not response_content:
        logger.warning(
            "LLM returned empty content, content_type=%s",
            type(assistant_response.content).__name__,
        )
        raise LLMRequestError("The language model returned an empty response")

    assistant_message = _to_memory_message(response_content)
    logger.info("LLM response received successfully")

    return response_content, [*validated_memory, user_message, assistant_message]
