from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog


class Config(BaseSettings):
    openai_api_key: str
    telegram_bot_token: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


config = Config()  # pyright:ignore[reportCallIssue]


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    cache_logger_on_first_use=True,
)
