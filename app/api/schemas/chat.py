from pydantic import BaseModel, Field, field_validator


class StartChatRequest(BaseModel):
    """Request body for creating a practice chat session."""

    video_id: int = Field(gt=0, examples=[42])


class StartChatResponse(BaseModel):
    """Response returned after a chat session is created."""

    session_id: int = Field(examples=[7])


class SendMessageRequest(BaseModel):
    """Request body for sending a user message to a chat session."""

    session_id: int = Field(gt=0, examples=[7])
    message: str = Field(
        min_length=1,
        examples=[
            "I would explain event-driven architecture as a way to decouple services."
        ],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Validate that the message is not empty after trimming."""
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Field message must not be empty")
        if len(normalized_value) > 4000:
            raise ValueError("Message is too long")
        return normalized_value


class SendMessageResponse(BaseModel):
    """Assistant response for a practice turn."""

    answer: str = Field(examples=["Quick score: 7/10\nWhat was good..."])


class ChatSessionItem(BaseModel):
    """Chat session list item."""

    id: int
    video_id: int | None = None
    title: str | None = None
    created_at: str


class ChatMessageItem(BaseModel):
    """Message history item for a chat session."""

    id: int
    role: str
    content: str
    created_at: str
