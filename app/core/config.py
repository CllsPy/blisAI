from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str
    tavily_api_key: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # App
    app_env: str = "development"
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()