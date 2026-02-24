from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str
    tavily_api_key: str

    # Redis
    redis_url: str = "redis://redis:6379"

    # App
    app_env: str = "production"
    log_level: str = "INFO"
    app_name: str = "Blis AI Travel API"
    app_version: str = "1.0.0"

    # RAG
    faiss_index_path: str = "./data/faiss_index"
    docs_path: str = "./docs/faq_data"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()