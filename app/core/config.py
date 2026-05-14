from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"

    # Database
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "pass"
    POSTGRES_DB: str = "careeros"
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/careeros"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM Providers
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Storage
    CV_STORAGE_PATH: str = "./storage/cvs"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
