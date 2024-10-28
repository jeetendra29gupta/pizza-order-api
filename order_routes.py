import logging
from typing import Literal, Dict, Any

from fastapi import APIRouter, status, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from log_config import setup_logging
from models import Order, User
from utils import date, get_current_user

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


class PlaceOrder(BaseModel):
    quantity: int
    pizza_size: Literal["small", "medium", "large", "extra-large"]
    flavour: bool


# Initialize the router
order_router = APIRouter(
    prefix="/orders",
    tags=['orders']
)


async def get_authenticated_user(token: str, db: Session) -> User:
    """Helper function to retrieve the authenticated user."""
    username = await get_current_user(token)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def format_order_response(order: Order) -> Dict[str, Any]:
    """Format the order details for response."""
    return {
        "id": order.id,
        "user_id": order.user.username,
        "quantity": order.quantity,
        "pizza_size": order.pizza_size,
        "flavour": order.flavour,
        "order_status": order.order_status,
    }


@order_router.post('/', response_model=dict, status_code=status.HTTP_201_CREATED)
async def place_an_order(
        order: PlaceOrder,
        db: Session = Depends(get_db),
        token: str = Header(...)
) -> Dict[str, Any]:
    """
    Place a new order for a pizza.

    Args:
        order (PlaceOrder): The order details including quantity, pizza size, and flavour.
        db (Session): The database session for accessing the database.
        token (str): The JWT token for user authentication.

    Returns:
        dict: A message detailing the result of the order placement and the order details.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        new_order = Order(
            quantity=order.quantity,
            order_status="pending",
            pizza_size=order.pizza_size,
            flavour=order.flavour,
            user=db_user  # Associate user directly
        )

        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        return {
            "detail": f"Order placed successfully, order ID {new_order.id}!",
            "order": format_order_response(new_order),
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the order."
        )


@order_router.get('/', response_model=dict, status_code=status.HTTP_200_OK)
async def list_all_orders(
        db: Session = Depends(get_db),
        token: str = Header(...)
) -> Dict[str, Any]:
    """
    List all orders for authorized staff users.

    Args:
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message and the list of all orders.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        if not db_user.is_staff:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not a superuser.")

        all_orders = db.query(Order).all()
        order_list = [format_order_response(order) for order in all_orders]

        return {
            "message": "List of all orders",
            "orders": order_list,
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while getting all orders."
        )


@order_router.get('/{oid}', response_model=dict, status_code=status.HTTP_200_OK)
async def get_order_by_id(oid: int, db: Session = Depends(get_db), token: str = Header(...)) -> Dict[str, Any]:
    """
    Retrieve a specific order by its ID for authorized staff users.

    Args:
        oid (int): The ID of the order to retrieve.
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message and the details of the requested order.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        if not db_user.is_staff:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not a superuser.")

        order = db.query(Order).filter(Order.id == oid).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        return {
            "message": "Order by ID retrieved successfully.",
            "order": format_order_response(order),
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving order with ID {oid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while getting the order."
        )


@order_router.get('/user/orders', response_model=dict, status_code=status.HTTP_200_OK)
async def get_user_orders(db: Session = Depends(get_db), token: str = Header(...)) -> Dict[str, Any]:
    """
    Retrieve all orders for the currently authenticated user.

    Args:
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message and the list of user's orders.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        user_orders = db_user.orders
        order_list = [format_order_response(order) for order in user_orders]

        return {
            "message": "User orders retrieved successfully.",
            "orders": order_list,
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving orders for user {db_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving user orders."
        )


@order_router.get('/user/order/{oid}', response_model=dict, status_code=status.HTTP_200_OK)
async def get_specific_order(oid: int, db: Session = Depends(get_db), token: str = Header(...)) -> Dict[str, Any]:
    """
    Retrieve a specific order for the currently authenticated user.

    Args:
        oid (int): The ID of the order to retrieve.
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message and the details of the specified order.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        order = db.query(Order).filter(Order.id == oid, Order.user_id == db_user.id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        return {
            "message": "Order retrieved successfully.",
            "order": format_order_response(order),
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving order ID {oid} for user {db_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the order."
        )


@order_router.put('/update/{oid}', response_model=dict, status_code=status.HTTP_200_OK)
async def update_order(
        oid: int,
        order: PlaceOrder,
        db: Session = Depends(get_db),
        token: str = Header(...)
) -> Dict[str, Any]:
    """
    Update an existing order for the currently authenticated user.

    Args:
        oid (int): The ID of the order to update.
        order (PlaceOrder): The new order details.
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message detailing the result of the order update and the updated order details.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        # Retrieve the existing order
        existing_order = db.query(Order).filter(Order.id == oid, Order.user_id == db_user.id).first()

        if not existing_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        # Update order details
        existing_order.quantity = order.quantity
        existing_order.pizza_size = order.pizza_size
        existing_order.flavour = order.flavour

        db.commit()
        db.refresh(existing_order)

        return {
            "detail": f"Order ID {existing_order.id} updated successfully!",
            "order": format_order_response(existing_order),
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error updating order ID {oid} for user {db_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the order."
        )


@order_router.put('/status/{oid}', response_model=dict, status_code=status.HTTP_200_OK)
async def update_order_status(
        oid: int,
        new_status: str,  # New status for the order
        db: Session = Depends(get_db),
        token: str = Header(...)
) -> dict:
    """
    Update the status of an existing order for super users.

    Args:
        oid (int): The ID of the order to update.
        new_status (str): The new status for the order.
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message detailing the result of the status update.
    """
    db_user = await get_authenticated_user(token, db)

    try:
        # Check if the user has staff privileges
        if not db_user.is_staff:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="You are not authorized to update order status.")

        # Retrieve the existing order
        order = db.query(Order).filter(Order.id == oid).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        # Update the order status
        order.order_status = new_status
        db.commit()
        db.refresh(order)

        return {
            "detail": f"Order ID {order.id} status updated successfully to '{new_status}'!",
            "order": format_order_response(order),
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error updating status for order ID {oid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the order status."
        )


@order_router.delete('/delete/{oid}', response_model=dict, status_code=status.HTTP_200_OK)
async def delete_order(
        oid: int,
        db: Session = Depends(get_db),
        token: str = Header(...)
) -> dict:
    """
    Delete an existing order for the authenticated user.

    Args:
        oid (int): The ID of the order to delete.
        db (Session): The database session for accessing the database.
        token (str): The JWT token for authentication.

    Returns:
        dict: A message detailing the result of the deletion.
    """
    db_user = await get_authenticated_user(token, db)
    try:
        # Retrieve the order by ID and ensure it belongs to the current user
        order = db.query(Order).filter(Order.id == oid, Order.user_id == db_user.id).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        # Delete the order
        db.delete(order)
        db.commit()

        return {
            "detail": f"Order ID {oid} deleted successfully.",
            "date_time": date,
        }

    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTP exceptions
    except Exception as e:
        logger.error(f"Error deleting order ID {oid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the order."
        )
