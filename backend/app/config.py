from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://eale:eale_secret@localhost:5432/eale"
    AUTO_SEED: bool = True
    USE_LLM_VARIANTS: bool = False
    # LLM context + grading (extension)
    USE_LLM_CONTEXT: bool = False
    USE_LLM_GRADING: bool = False
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    LLM_CACHE_TTL_SECONDS: int = 600
    CORS_ORIGINS: str = "*"
    SCHEDULER_INTERVAL_SECONDS: int = 60

    # Spaced repetition intervals (days)
    RETEST_INTERVALS_DAYS: list[int] = [1, 3, 7]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
