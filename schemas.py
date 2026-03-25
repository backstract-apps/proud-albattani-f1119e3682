from pydantic import BaseModel,Field,field_validator

import datetime

import uuid

from typing import Any, Dict, List,Optional,Tuple,Union

import re

class Products(BaseModel):
    product_name: Optional[str]=None
    price: Optional[str]=None
    stock: Optional[Union[int, float]]=None


class ReadProducts(BaseModel):
    product_name: Optional[str]=None
    price: Optional[str]=None
    stock: Optional[Union[int, float]]=None
    class Config:
        from_attributes = True


class Newtable(BaseModel):
    email: Optional[str]=None
    mobile: Optional[Union[int, float]]=None
    password: Optional[str]=None


class ReadNewtable(BaseModel):
    email: Optional[str]=None
    mobile: Optional[Union[int, float]]=None
    password: Optional[str]=None
    class Config:
        from_attributes = True


class Users(BaseModel):
    name: str
    email: str
    created_at: Optional[datetime.time]=None
    phone: Optional[str]=None
    password: Optional[str]=None


class ReadUsers(BaseModel):
    name: str
    email: str
    created_at: Optional[datetime.time]=None
    phone: Optional[str]=None
    password: Optional[str]=None
    class Config:
        from_attributes = True


class Students(BaseModel):
    email: Optional[str]=None
    password: Optional[str]=None


class ReadStudents(BaseModel):
    email: Optional[str]=None
    password: Optional[str]=None
    class Config:
        from_attributes = True


class ShivamAuth(BaseModel):
    email: Optional[str]=None
    password: Optional[str]=None
    mobile: Optional[str]=None


class ReadShivamAuth(BaseModel):
    email: Optional[str]=None
    password: Optional[str]=None
    mobile: Optional[str]=None
    class Config:
        from_attributes = True


class Orders(BaseModel):
    user_id: Optional[Union[int, float]]=None
    product_id: Optional[Union[int, float]]=None
    quantity: Optional[Union[int, float]]=None
    order_date: Optional[datetime.time]=None


class ReadOrders(BaseModel):
    user_id: Optional[Union[int, float]]=None
    product_id: Optional[Union[int, float]]=None
    quantity: Optional[Union[int, float]]=None
    order_date: Optional[datetime.time]=None
    class Config:
        from_attributes = True


class ItemsSold(BaseModel):
    quantity: Optional[Union[int, float]]=None
    price_per_item: Optional[Union[int, float]]=None
    price: Optional[float]=None


class ReadItemsSold(BaseModel):
    quantity: Optional[Union[int, float]]=None
    price_per_item: Optional[Union[int, float]]=None
    price: Optional[float]=None
    class Config:
        from_attributes = True


class Emp1(BaseModel):
    email: Optional[str]=None
    password: Optional[str]=None


class ReadEmp1(BaseModel):
    email: Optional[str]=None
    password: Optional[str]=None
    class Config:
        from_attributes = True


class AbgUsers(BaseModel):
    email: Optional[str]=None
    mobile: Optional[Union[int, float]]=None
    password: Optional[str]=None


class ReadAbgUsers(BaseModel):
    email: Optional[str]=None
    mobile: Optional[Union[int, float]]=None
    password: Optional[str]=None
    class Config:
        from_attributes = True


class MaysonRequestLogger(BaseModel):
    ts_utc: Optional[datetime.time]=None
    method: Optional[str]=None
    path: Optional[str]=None
    status_code: Optional[Union[int, float]]=None
    duration_ms: Optional[float]=None
    client_ip: Optional[str]=None
    user_agent: Optional[str]=None
    content_length: Optional[Union[int, float]]=None
    style: Optional[str]=None
    message: Optional[str]=None
    query_params: Optional[str]=None


class ReadMaysonRequestLogger(BaseModel):
    ts_utc: Optional[datetime.time]=None
    method: Optional[str]=None
    path: Optional[str]=None
    status_code: Optional[Union[int, float]]=None
    duration_ms: Optional[float]=None
    client_ip: Optional[str]=None
    user_agent: Optional[str]=None
    content_length: Optional[Union[int, float]]=None
    style: Optional[str]=None
    message: Optional[str]=None
    query_params: Optional[str]=None
    class Config:
        from_attributes = True


class MaysonPlatformAuthOtp(BaseModel):
    email: str
    otp: str
    validity: Optional[str]=None
    created_at: datetime.time


class ReadMaysonPlatformAuthOtp(BaseModel):
    email: str
    otp: str
    validity: Optional[str]=None
    created_at: datetime.time
    class Config:
        from_attributes = True


