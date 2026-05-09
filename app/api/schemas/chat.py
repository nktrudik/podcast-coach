from pydantic import BaseModel, Field, field_validator


class StartChatRequest(BaseModel):
    """Запрос на создание новой чат-сессии."""

    video_id: int = Field(gt=0)


class StartChatResponse(BaseModel):
    """Ответ после создания чат-сессии."""

    session_id: int


class SendMessageRequest(BaseModel):
    """Запрос на отправку сообщения в чат-сессию."""

    session_id: int = Field(gt=0)
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Проверяет, что сообщение не пустое после trim."""
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Поле message не должно быть пустым")
        if len(normalized_value) > 4000:
            raise ValueError("Сообщение слишком длинное")
        return normalized_value


class SendMessageResponse(BaseModel):
    """Ответ с сообщением ассистента."""

    answer: str


class ChatSessionItem(BaseModel):
    """Элемент списка чат-сессий."""

    id: int
    video_id: int | None = None
    title: str | None = None
    created_at: str


class ChatMessageItem(BaseModel):
    """Элемент истории сообщений конкретной сессии."""

    id: int
    role: str
    content: str
    created_at: str
