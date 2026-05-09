from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Настройки frontend-интерфейса Streamlit."""

    backend_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FRONTEND_BACKEND_BASE_URL", "BACKEND_BASE_URL"),
    )
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    frontend_request_timeout_seconds: float = Field(default=180.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_backend_base_url(self) -> str:
        """Возвращает итоговый URL backend для HTTP-запросов."""
        if self.backend_base_url and self.backend_base_url.strip():
            return self.backend_base_url.strip().rstrip("/")

        return f"http://{self.host}:{self.port}"


settings = FrontendSettings()
