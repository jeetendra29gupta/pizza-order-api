import uvicorn
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from auth_routes import auth_router
from models import init_db
from order_routes import order_router

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the database
init_db()


@app.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def index() -> dict:
    """Welcome endpoint.

    Returns:
        dict: A welcome message for the Pizza Delivery API.
    """
    return {
        "message": "Welcome to the Pizza Delivery API!",
    }


app.include_router(auth_router)
app.include_router(order_router)

if __name__ == '__main__':
    uvicorn.run("main_app:app", host="0.0.0.0", port=8181, reload=True)
