from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import class_mapper
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, Float, Text, ForeignKey, JSON, Numeric, Date, \
    TIMESTAMP, UUID, LargeBinary, text, Interval
from sqlalchemy.types import Enum
from sqlalchemy.ext.declarative import declarative_base


@as_declarative()
class Base:
    id: int
    __name__: str

    # Auto-generate table name if not provided
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    # Generic to_dict() method
    def to_dict(self):
        """
        Converts the SQLAlchemy model instance to a dictionary, ensuring UUID fields are converted to strings.
        """
        result = {}
        for column in class_mapper(self.__class__).columns:
            value = getattr(self, column.key)
                # Handle UUID fields
            if isinstance(value, uuid.UUID):
                value = str(value)
            # Handle datetime fields
            elif isinstance(value, datetime):
                value = value.isoformat()  # Convert to ISO 8601 string
            # Handle Decimal fields
            elif isinstance(value, Decimal):
                value = float(value)

            result[column.key] = value
        return result




class Products(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String, nullable=True)
    price = Column(String, nullable=True)
    stock = Column(Integer, nullable=True)


class Newtable(Base):
    __tablename__ = "newtable"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=True)
    mobile = Column(Integer, nullable=True)
    password = Column(String, nullable=True)


class Users(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    email = Column(String)
    created_at = Column(Time, nullable=True, server_default=text("now()"))
    phone = Column(String, nullable=True)
    password = Column(String, nullable=True)


class Students(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=True)
    password = Column(String, nullable=True)


class ShivamAuth(Base):
    __tablename__ = "shivam_auth"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=True)
    password = Column(String, nullable=True)
    mobile = Column(String, nullable=True)


class Orders(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    product_id = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    order_date = Column(Time, nullable=True, server_default=text("now()"))


class ItemsSold(Base):
    __tablename__ = "items_sold"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    quantity = Column(Integer, nullable=True)
    price_per_item = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)


class Emp1(Base):
    __tablename__ = "emp1"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=True)
    password = Column(String, nullable=True)


class AbgUsers(Base):
    __tablename__ = "abg_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=True)
    mobile = Column(Integer, nullable=True)
    password = Column(String, nullable=True)


class MaysonRequestLogger(Base):
    __tablename__ = "mayson_request_logger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_utc = Column(Time, nullable=True, server_default=text("now()"))
    method = Column(String, nullable=True)
    path = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    content_length = Column(Integer, nullable=True)
    style = Column(String, nullable=True)
    message = Column(String, nullable=True)
    query_params = Column(String, nullable=True)


class MaysonPlatformAuthOtp(Base):
    __tablename__ = "mayson_platform_auth_otp"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String)
    otp = Column(String)
    validity = Column(String, nullable=True)
    created_at = Column(Time, server_default=text("now()"))


