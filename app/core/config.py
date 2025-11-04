"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres_dev_password@localhost:5432/ai_judge"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector Database
    WEAVIATE_URL: str = "http://localhost:8080"
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    
    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Legal Domain
    JURISDICTION: str = "federal"
    LEGAL_DOMAIN: str = "contract_disputes"
    CASE_YEARS_LOOKBACK: int = 20
    
    # RAG Configuration
    VECTOR_DIMENSION: int = 3072
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 10
    RERANK_TOP_K: int = 5
    
    # LLM Configuration
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.1
    
    # CourtListener API
    COURTLISTENER_API_KEY: str = ""
    COURTLISTENER_API_TOKEN: str = ""
    
    # CORS
    # Add frontend dev origins here (e.g. localhost:3000, localhost:3003).
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3003",
        "http://localhost:8000",
        "https://verdictbnb.ai",
        "https://www.verdictbnb.ai",
        "https://lawl.vercel.app",
    ]
    
    # Data Paths
    DATA_RAW_PATH: str = "/data/raw"
    DATA_PROCESSED_PATH: str = "/data/processed"
    DATA_EMBEDDINGS_PATH: str = "/data/embeddings"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()






