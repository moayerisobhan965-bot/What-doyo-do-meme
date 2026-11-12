"""
Application Configuration
Lädt und validiert alle Umgebungsvariablen
"""
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Zentrale Konfigurationsklasse"""

    # App
    APP_NAME: str = "What Meme"
    APP_ENV: str = "production"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@postgres:5432/whatmeme"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change_this_to_a_very_long_random_string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Email
    SMTP_HOST: str = "smtp.resend.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey"
    SMTP_PASSWORD: str = "your_resend_api_key_here"
    SMTP_FROM: str = "noreply@whatmeme.de"
    SMTP_FROM_NAME: str = "What Meme"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 5
    RATE_LIMIT_BURST: int = 10

    # Game
    MAX_PLAYERS_PER_ROOM: int = 10
    MIN_PLAYERS_TO_START: int = 2
    WIN_SCORE: int = 5
    MAX_CAPTIONS_PER_ROUND: int = 5
    MAX_GAME_DURATION_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: str = "https://whatmeme.de,http://localhost:3000"

    # Meme
    MEME_STORAGE_PATH: str = "/app/static/memes"
    MEME_DOWNLOAD_DELAY: float = 0.1

    # SSL
    ENABLE_SSL: bool = True
    SSL_CERT_PATH: str = "/etc/letsencrypt/live/whatmeme.de/fullchain.pem"
    SSL_KEY_PATH: str = "/etc/letsencrypt/live/whatmeme.de/privkey.pem"

    # Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_HEALTH_CHECK: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        """Liste der erlaubten CORS-Origins"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def database_pool_settings(self):
        """Datenbank-Pool-Einstellungen"""
        return {
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }

    @property
    def redis_pool_settings(self):
        """Redis-Pool-Einstellungen"""
        return {
            "max_connections": 20,
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Gibt die Settings-Instanz zurück (Singleton-Pattern)"""
    return Settings()
