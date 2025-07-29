from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database - Using PostgreSQL
    database_url: str = "postgresql://sales_user:sales_password@localhost/sales_calls"
    database_url_async: str = "postgresql+asyncpg://sales_user:sales_password@localhost/sales_calls"
    
    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Sales Call Analytics API"
    version: str = "1.0.0"
    
    # Security
    secret_key: str = "prarabdha"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI (optional)
    openai_api_key: Optional[str] = None
    
    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379"
    
    # Model settings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sentiment_model: str = "distilbert-base-uncased-finetuned-sst-2-english"
    
    # Master API Token for admin/bypass
    master_api_token: str = "MASTER_SUPER_SECRET_TOKEN"
    
    class Config:
        env_file = ".env"


settings = Settings() 