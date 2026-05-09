from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    anthropic_api_key: str
    database_url: str
    environment: str = "development"
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:3000"
    upload_dir: Path = Path("data/uploads")
    openai_api_key: Optional[str] = None
    chroma_persist_dir: str = "data/chroma"
    embedding_model: str = "text-embedding-3-large"


settings = Settings()
