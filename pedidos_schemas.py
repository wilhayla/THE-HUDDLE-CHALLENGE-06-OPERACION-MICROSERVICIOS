from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class OrderBase(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    total_price: float

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None

class Order(OrderBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

    #model_config = ConfigDict(from_attributes=True)

    