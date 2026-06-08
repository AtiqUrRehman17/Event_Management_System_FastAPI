from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
import uuid
from .config import settings
from .exceptions import TokenExpiredException, InvalidTokenException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


class Security:

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        

        now = datetime.now(timezone.utc)

        # Calculate expiry
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Build token payload
        to_encode = {
            # Standard JWT claims
            "sub": data.get("sub"),
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "iss": settings.APP_NAME,

            # Custom claims
            "type": "access",
        }

        # Add user info if provided
        if user_info:
            to_encode["username"] = user_info.get("username")
            to_encode["email"] = user_info.get("email")
            to_encode["role"] = user_info.get("role")

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None
    ) -> str:
        
        
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Build token payload
        to_encode = {
            # Standard JWT claims
            "sub": data.get("sub"),
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "iss": settings.APP_NAME,

            # Custom claims
            "type": "refresh",
        }

        # Add minimal user info for refresh token
        if user_info:
            to_encode["username"] = user_info.get("username")

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify JWT token and return payload.
        Validates signature, expiry, issuer, and token type.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                issuer=settings.APP_NAME
            )

            # Check token type
            if payload.get("type") != token_type:
                raise InvalidTokenException()

            return payload

        except ExpiredSignatureError:
            raise TokenExpiredException()
        except InvalidTokenError:
            raise InvalidTokenException()

    @staticmethod
    def get_token_claims(token: str) -> Dict[str, Any]:
        """
        Decode token WITHOUT verification.
        Useful for reading claims from expired tokens.
        DO NOT use this for authentication.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False}
            )
            return payload
        except InvalidTokenError:
            raise InvalidTokenException()


async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = security
) -> Optional[str]:
    """Dependency to get current token from request"""
    if not credentials:
        return None
    return credentials.credentials