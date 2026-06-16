from pydantic_settings import BaseSettings
from typing import Optional
import secrets
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Event Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./event_management.db"
    SQLALCHEMY_ECHO: bool = False

    # JWT Configuration - NO DEFAULT VALUE
    SECRET_KEY: Optional[str] = None
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
    EMAIL_PROVIDER: str = "smtp"
    POSTMARK_API_TOKEN: str = ""

    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:8000"

    # Reset Token Configuration
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Email Verification Configuration
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REQUIRE_EMAIL_VERIFICATION: bool = True
    TESTING: bool = False
    AUTO_COPY_ENV: bool = True

    # Image Upload Configuration
    UPLOAD_DIR: str = "uploads"
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_secret_key()
        self._apply_dev_defaults()

    def _is_email_configured(self) -> bool:
        """Check if email sending is actually configured"""
        if self.EMAIL_PROVIDER == "postmark":
            return bool(self.POSTMARK_API_TOKEN)
        return bool(self.EMAIL_HOST_USER and self.EMAIL_HOST_PASSWORD and self.DEFAULT_FROM_EMAIL)

    def _apply_dev_defaults(self) -> None:
        """Apply smart defaults for development mode"""
        if self.TESTING:
            return
        if self.DEBUG and not self._is_email_configured():
            if self.REQUIRE_EMAIL_VERIFICATION:
                self.REQUIRE_EMAIL_VERIFICATION = False
                print("=" * 60)
                print("DEV MODE: Email not configured, disabling REQUIRE_EMAIL_VERIFICATION")
                print("Set EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL")
                print("in your .env file to enable email features.")
                print("=" * 60)

    def _validate_secret_key(self) -> None:
        """Validate that SECRET_KEY is properly configured"""
        
        # Check if SECRET_KEY is set
        if not self.SECRET_KEY:
            if self.DEBUG:
                # In development, generate a random key and warn
                self.SECRET_KEY = secrets.token_urlsafe(32)
                print("=" * 60)
                print("WARNING: SECRET_KEY not set in .env file!")
                print(f"Generated random key for development: {self.SECRET_KEY}")
                print("For production, please set a secure SECRET_KEY in your .env file!")
                print("=" * 60)
            else:
                # In production, fail hard
                raise ValueError(
                    "\n" + "=" * 60 + "\n"
                    "SECURITY ERROR: SECRET_KEY is required in production mode!\n"
                    "Please set a secure SECRET_KEY in your .env file.\n"
                    "You can generate one using:\n"
                    "    python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
                    + "=" * 60
                )
        
        # Validate key strength for production
        if not self.DEBUG and len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"\n" + "=" * 60 + "\n"
                f"❌ SECURITY ERROR: SECRET_KEY is too weak ({len(self.SECRET_KEY)} characters).\n"
                f"Minimum required is 32 characters for HS256.\n"
                f"Generate a new key using:\n"
                f"    python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
                + "=" * 60
            )
        
        # Check for common weak keys
        weak_keys = ["mysecretkey", "secret", "password", "changeme", "your-super-secret-key-change-this-in-production"]
        if self.SECRET_KEY and self.SECRET_KEY.lower() in weak_keys:
            if self.DEBUG:
                print("=" * 60)
                print("WARNING: You are using a weak SECRET_KEY!")
                print("Please generate a strong key for production use.")
                print("=" * 60)
            else:
                raise ValueError(
                    "\n" + "=" * 60 + "\n"
                    "SECURITY ERROR: SECRET_KEY is too weak for production!\n"
                    f"Current key '{self.SECRET_KEY}' is commonly used and insecure.\n"
                    "Generate a strong random key using:\n"
                    "    python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
                    + "=" * 60
                )


settings = Settings()