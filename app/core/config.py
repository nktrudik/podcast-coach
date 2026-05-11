from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения."""

    api_key: str
    admin_api_key: str
    stt_model_name: str = "mistralai/voxtral-small-24b-2507"
    llm_model_name: str = "inclusionai/ring-2.6-1t:free"
    base_url: str = "https://openrouter.ai/api/v1"
    db_path: str = "./storage/database.db"
    log_level: str = "INFO"
    log_file_path: str = "./storage/logs/backend.log"
    external_request_timeout_seconds: float = Field(default=45.0, gt=0)
    external_request_max_attempts: int = Field(default=3, ge=1, le=10)
    external_request_retry_delay_seconds: float = Field(default=3.0, ge=0)
    stt_request_max_attempts: int = Field(default=6, ge=1, le=12)
    stt_request_retry_delay_seconds: float = Field(default=4.0, ge=0)
    llm_memory_messages_limit: int = Field(default=5, ge=1, le=30)
    max_video_duration_minutes: int = Field(default=30, ge=1, le=240)
    youtube_cookies_file: str | None = None
    youtube_max_retries: int = Field(default=3, ge=1, le=10)
    youtube_retry_delay_seconds: float = Field(default=10.0, ge=0)
    uploaded_videos_limit: int = Field(default=5, ge=1, le=100)
    chat_sessions_per_video_limit: int = Field(default=5, ge=1, le=50)
    youtube_url: str = (
        "https://www.youtube.com/watch?v=gO1Cm_A_pO8&list=PLZwUC1tATQdzM24SU_17Qox5-a20fBP_T"
    )
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    model_config = SettingsConfigDict(
        env_file=(".env", "/etc/secrets/.env", "/etc/secrets/env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
