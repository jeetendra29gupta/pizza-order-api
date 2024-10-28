import logging

from fastapi import APIRouter, status, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from log_config import setup_logging
from models import User
from utils import hash_password, verify_password, create_token, get_current_user, date

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


# Pydantic models for user data
class LoginUser(BaseModel):
    username: str
    password: str


class SignupUser(LoginUser):
    email: str


# Initialize the router
auth_router = APIRouter(prefix='/auth', tags=['auth'])


@auth_router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(user: SignupUser, db: Session = Depends(get_db)) -> dict:
    """Create a new user.

    Args:
        user (SignupUser): User signup details including username, password, and email.
        db (Session): Database session.

    Returns:
        dict: Confirmation message with user details.
    """
    try:
        # Check if the username already exists
        if db.query(User).filter(User.username == user.username).first():
            error_message = f"Username: {user.username}, already registered"
            logger.error(error_message)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)

        # Check if the email already exists
        if db.query(User).filter(User.email == user.email).first():
            error_message = f"Email ID: {user.email}, already registered"
            logger.error(error_message)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)

        # Hash the password and create the new user
        hashed_password = hash_password(user.password)
        new_user = User(username=user.username, email=user.email, password=hashed_password)

        # Add the new user to the database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "detail": f"User created successfully, user ID {new_user.id}!",
            "user": {"email": new_user.email, "username": new_user.username},
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred while creating the user.")


@auth_router.post("/login", response_model=dict, status_code=status.HTTP_200_OK)
async def login(user: LoginUser, db: Session = Depends(get_db)) -> dict:
    """Authenticate a user and return tokens.

    Args:
        user (LoginUser): User login details including username and password.
        db (Session): Database session.

    Returns:
        dict: Confirmation message and access tokens.
    """
    try:
        # Retrieve the user by username
        db_user = db.query(User).filter(User.username == user.username).first()

        if db_user is None:
            error_message = "Invalid username"
            logger.error(error_message)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)

        # Verify the password
        if not verify_password(user.password, db_user.password):
            error_message = "Invalid password"
            logger.error(error_message)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)

        # Create tokens for the user
        tokens = create_token(db_user.username)

        return {
            "detail": "Login successful",
            "date_time": date,
            "token": tokens,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during login.")


@auth_router.get('/', response_model=dict, status_code=status.HTTP_200_OK)
async def auth_index() -> dict:
    """Sample hello world route.

    Returns:
        dict: Greeting message.
    """
    return {
        "message": "Hello World",
        "date_time": date,
    }


@auth_router.get('/message', response_model=dict, status_code=status.HTTP_200_OK)
async def auth_message(token: str = Header(...)) -> dict:
    """Protected route that returns a greeting message.

    Args:
        token (str): JWT token from the request header.

    Returns:
        dict: Greeting message and the current user.
    """
    try:
        current_user = await get_current_user(token)
        return {
            "message": "Hello World",
            "date_time": date,
            "user": current_user,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error during auth_message: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred during auth message.")


@auth_router.get('/refresh', response_model=dict, status_code=status.HTTP_200_OK)
async def refresh_token(token: str = Header(...)) -> dict:
    """Refresh the user's token.

    Args:
        token (str): JWT token from the request header.

    Returns:
        dict: Confirmation message and new tokens.
    """
    try:
        current_user = await get_current_user(token)
        tokens = create_token(current_user)

        return {
            "detail": "Token is refreshed",
            "date_time": date,
            "token": tokens,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error during refresh_token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred during refresh token.")
