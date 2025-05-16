from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

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
