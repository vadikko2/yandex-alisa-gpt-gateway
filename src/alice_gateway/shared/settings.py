from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SYSTEM_PROMPT_PATH = "prompts/alice_system.md"


def read_system_prompt(path: str | Path, *, base_dir: Path | None = None) -> str:
    prompt_path = Path(path)
    if not prompt_path.is_absolute():
        root = base_dir if base_dir is not None else Path.cwd()
        prompt_path = root / prompt_path
    if not prompt_path.is_file():
        raise FileNotFoundError(f"system prompt file not found: {prompt_path}")
    text = prompt_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"system prompt file is empty: {prompt_path}")
    return text


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    timeweb_api_key: str = Field(default="", validation_alias="TIMEWEB_API_KEY")
    timeweb_base_url: str = Field(default="", validation_alias="TIMEWEB_BASE_URL")
    timeweb_model: str = Field(default="deepseek-v4-flash", validation_alias="TIMEWEB_MODEL")
    system_prompt_path: str = Field(
        default=DEFAULT_SYSTEM_PROMPT_PATH,
        validation_alias="SYSTEM_PROMPT_PATH",
    )
    alice_reply_budget_seconds: float = Field(default=3.0, validation_alias="ALICE_REPLY_BUDGET_SECONDS")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8080, validation_alias="PORT")
    system_prompt: str = Field(default="", exclude=True)


def load_settings(*, base_dir: Path | None = None) -> Settings:
    settings = Settings()
    prompt = read_system_prompt(settings.system_prompt_path, base_dir=base_dir)
    return settings.model_copy(update={"system_prompt": prompt})
