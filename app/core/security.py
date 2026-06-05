from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from .config import settings
from .exceptions import TokenExpiredException, InvalidTokenException


class Security:
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify JWT token and return payload
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                raise InvalidTokenException()
            
            return payload
        except ExpiredSignatureError:
            raise TokenExpiredException()
        except InvalidTokenError:
            raise InvalidTokenException()
    
    @staticmethod
    def get_token_from_header(authorization: Optional[str]) -> str:
        """
        Extract token from Authorization header
        """
        if not authorization:
            raise InvalidTokenException()
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise InvalidTokenException()
        
        token = parts[1]
        if not token:
            raise InvalidTokenException()
        
        return token


# OAuth2 scheme for FastAPI
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


async def get_current_token(credentials: Optional[HTTPAuthorizationCredentials] = security) -> Optional[str]:
    """
    Dependency to get current token from request
    """
    if not credentials:
        return None
    return credentials.credentials