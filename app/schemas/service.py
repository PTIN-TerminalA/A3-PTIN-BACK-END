from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import time

class ServiceSchema(BaseModel):
    id: int
    name: str
    description: str
    link: str
    ad_path: str
    avg_price: int
    location_x: Decimal
    location_y: Decimal
    status: str
    offer: Optional[str]

    class Config:
        orm_mode = True


class PriceSchema(BaseModel):
    avg_price: int

    class Config:
        orm_mode = True

class ScheduleSchema(BaseModel):
    service_id: int
    day: str
    opening_hour: time
    closing_hour: time

    class Config:
        orm_mode = True

class ServiceTagSchema(BaseModel):
    service_id: int
    tag_name: str

    class Config:
        orm_mode = True

class ValorationSchema(BaseModel):
    service_id: int
    user_id: int
    value: Decimal
    description: Optional[str]

    class Config:
        orm_mode = True

