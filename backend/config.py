from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    assessor_model: str = Field(default="gpt-4o", env="ASSESSOR_MODEL")
    parser_model: str = Field(default="gpt-4o-mini", env="PARSER_MODEL")
    planner_model: str = Field(default="gpt-4o", env="PLANNER_MODEL")
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/skill_assessment",
        env="DATABASE_URL",
    )

    # Tavily
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")

    # App
    app_env: str = Field(default="development", env="APP_ENV")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS",
    )

    # Session / Assessment config
    session_ttl_seconds: int = Field(default=7200, env="SESSION_TTL_SECONDS")
    max_questions_per_skill: int = Field(default=4, env="MAX_QUESTIONS_PER_SKILL")
    confidence_threshold: float = Field(default=0.85, env="CONFIDENCE_THRESHOLD")

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()