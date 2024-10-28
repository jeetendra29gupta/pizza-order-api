import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError

# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "Secret_Key-2024")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password (str): The plain text password.

    Returns:
        str: The hashed password.
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password.

    Args:
        plain_password (str): The plain text password.
        hashed_password (str): The hashed password.

    Returns:
        bool: True if the password matches, otherwise False.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_token(subject: str) -> dict:
    """Create a JWT token.

    Args:
        subject (str): The subject for the token.

    Returns:
        dict: The encoded JWT tokens like access and refresh.
    """

    # Create access token
    access_token = jwt.encode(
        {
            "sub": subject,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    # Create refresh token
    refresh_token = jwt.encode(
        {
            "sub": subject,
            "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "token_type": "bearer",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def get_current_user(token: str) -> str:
    """Get the current user's username from the token.

    Args:
        token (str): The JWT token.

    Returns:
        str: The username of the current user.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

        return username

    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
