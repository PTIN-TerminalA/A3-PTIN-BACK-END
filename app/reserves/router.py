from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Route(BaseModel):
    start_location: str
    end_location: str
    vehicle_id: str
    scheduled_time: Optional[datetime]
