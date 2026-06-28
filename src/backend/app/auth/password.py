"""Password hashing utilities."""

from passlib.context import CryptContext

# Create password context with argon2 as primary (better compatibility)
# and bcrypt as fallback for verification of existing hashes
_pwd_context = None


def _get_pwd_context():
    """Lazy initialize password context to avoid bcrypt compatibility issues."""
    global _pwd_context
    if _pwd_context is None:
        _pwd_context = CryptContext(
            schemes=["argon2", "bcrypt"],
            deprecated="bcrypt"
        )
    return _pwd_context


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password.
    """
    pwd_context = _get_pwd_context()
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.

    Args:
        plain_password: The plaintext password to verify.
        hashed_password: The hashed password to verify against.

    Returns:
        True if the password matches, False otherwise.
    """
    pwd_context = _get_pwd_context()
    return pwd_context.verify(plain_password, hashed_password)
