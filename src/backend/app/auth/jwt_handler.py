"""JWT token generation and validation utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user ID to include in the token.
        expires_delta: Optional timedelta for token expiry. If not provided,
                      uses settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        The encoded JWT token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Calculate expiration time
    expire = datetime.now(timezone.utc) + expires_delta

    # Create token payload
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
    }

    # Encode and return token
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        The decoded token payload as a dictionary, or None if token is invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
