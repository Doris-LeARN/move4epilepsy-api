"""
Configuration de l'application - SÉCURISÉE
"""
from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator, Field
import secrets
import os


class Settings(BaseSettings):
    """Paramètres de l'application"""
    
    # Informations du projet
    PROJECT_NAME: str = "Move4Epilepsy API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse BACKEND_CORS_ORIGINS depuis une chaîne séparée par des virgules"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # Sécurité - OBLIGATOIRE en production
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # secondes
    
    # Base de données PostgreSQL
    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/move4epilepsy")
    
    # Environnement
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    FORCE_HTTPS: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    # Sécurité supplémentaire
    ALLOWED_HOSTS: List[str] = ["*"]
    SECURE_COOKIES: bool = True
    ALLOW_CREDENTIALS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validation en production
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY or self.SECRET_KEY == "":
                raise ValueError("❌ SECRET_KEY MUST be set in production via .env")
            
            if self.DEBUG:
                raise ValueError("❌ DEBUG must be False in production")
            
            if not self.FORCE_HTTPS:
                print("⚠️  WARNING: FORCE_HTTPS is disabled in production. Consider enabling it.")


settings = Settings()
