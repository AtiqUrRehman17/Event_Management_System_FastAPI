from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Event Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./event_management.db"
    SQLALCHEMY_ECHO: bool = False

    # JWT Configuration
    SECRET_KEY: str = "mysecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Default Admin Credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "Admin@1234"
    ADMIN_FIRST_NAME: str = "Super"
    ADMIN_LAST_NAME: str = "Admin"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()