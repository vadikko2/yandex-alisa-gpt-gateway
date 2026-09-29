from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SYSTEM_PROMPT = (
    "Ты голосовой собеседник в навыке Яндекс Алисы. "
    "Отвечай по-русски, коротко и разговорно, не больше четырёх предложений. "
    "Без markdown, таблиц и длинных списков."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    timeweb_api_key: str = Field(default="", validation_alias="TIMEWEB_API_KEY")
    timeweb_base_url: str = Field(default="", validation_alias="TIMEWEB_BASE_URL")
    timeweb_model: str = Field(default="deepseek-v4-flash", validation_alias="TIMEWEB_MODEL")
    system_prompt: str = Field(default=DEFAULT_SYSTEM_PROMPT, validation_alias="SYSTEM_PROMPT")
    alice_reply_budget_seconds: float = Field(default=3.0, validation_alias="ALICE_REPLY_BUDGET_SECONDS")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8080, validation_alias="PORT")


def load_settings() -> Settings:
    return Settings()
