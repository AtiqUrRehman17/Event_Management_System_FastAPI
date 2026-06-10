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

    # Email Configuration
    DEFAULT_FROM_EMAIL: str = ""
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: str = ""
    POSTMARK_API_TOKEN: Optional[str] = None
    EMAIL_PROVIDER: str = "postmarkapp"

    # Reset Token Configuration
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Email Verification Configuration
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440
    REQUIRE_EMAIL_VERIFICATION: bool = True

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # LinkedIn OAuth Configuration
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/linkedin/callback"

    # Facebook OAuth Configuration
    FACEBOOK_CLIENT_ID: str = ""
    FACEBOOK_CLIENT_SECRET: str = ""
    FACEBOOK_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/facebook/callback"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()