"""Configuration management using Pydantic settings"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str
    
    # Google Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "GEMINI_MODEL=gemini-1.5-flash"
    
    # App
    WEBHOOK_SECRET: str
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()