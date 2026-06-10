from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)

    @field_validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Reset token received via email")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        new_password = info.data.get('new_password')
        if new_password is not None and v != new_password:
            raise ValueError('Passwords do not match')
        return v

    @field_validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class EmailVerificationRequest(BaseModel):
    token: str = Field(..., description="Verification token received via email")


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


class GoogleAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used")


class LinkedInAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from LinkedIn")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used")


class FacebookAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Facebook")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"