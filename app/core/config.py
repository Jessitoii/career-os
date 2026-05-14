from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
import os
import shutil

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"

    # System State
    DRY_RUN: bool = True
    GLOBAL_KILL_SWITCH_KEY: str = "careeros:kill_switch"

    # Database
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "pass"
    POSTGRES_DB: str = "careeros"
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/careeros"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telemetry & Storage
    CV_STORAGE_PATH: str = "./storage/cvs"
    RESUME_MASTER_DIR: str = "./data/resumes/master"
    RESUME_FALLBACK_DIR: str = "./data/resumes/fallback"
    RESUME_GENERATED_DIR: str = "./data/resumes/generated"
    
    # Playwright Settings
    PLAYWRIGHT_HEADLESS: bool = False
    PLAYWRIGHT_SLOW_MO: int = 200
    RECORD_VIDEO_DIR: str = "./storage/traces/videos"
    TRACE_DIR: str = "./storage/traces"

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

    @model_validator(mode='after')
    def validate_dependencies(self) -> 'Settings':
        """Ensure critical external dependencies are met on boot."""
        # 1. Directories
        os.makedirs(self.CV_STORAGE_PATH, exist_ok=True)
        os.makedirs(self.RESUME_MASTER_DIR, exist_ok=True)
        os.makedirs(self.RESUME_FALLBACK_DIR, exist_ok=True)
        os.makedirs(self.RESUME_GENERATED_DIR, exist_ok=True)
        os.makedirs(self.RECORD_VIDEO_DIR, exist_ok=True)
        os.makedirs(self.TRACE_DIR, exist_ok=True)
        
        # 2. Validation
        if not self.GROQ_API_KEY and not self.CEREBRAS_API_KEY:
            raise ValueError("CRITICAL: At least one LLM provider API key (GROQ or CEREBRAS) must be set.")
            
        return self

settings = Settings()
