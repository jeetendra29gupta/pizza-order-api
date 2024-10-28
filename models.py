from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship, declarative_base

from database import engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)

    orders = relationship("Order", back_populates="user")


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False)
    order_status = Column(Enum("pending", "in-progress", "delivered", name="order_status"), nullable=False)
    pizza_size = Column(Enum("small", "medium", "large", "extra-large", name="pizza_size"), nullable=False)
    flavour = Column(Boolean, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="orders")


def init_db():
    Base.metadata.create_all(bind=engine)
