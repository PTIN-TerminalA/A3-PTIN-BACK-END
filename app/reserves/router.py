# app/reserves/router.py

from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class Route(BaseModel):
    start_location: str
    end_location: str
    scheduled_time: datetime
    state: Literal["En curs", "Programada", "Finalitzada"]

    class Config:
        schema_extra = {
            "example": {
                "start_location": "Porta A3",
                "end_location": "McDonald's",
                "scheduled_time": "2025-04-20T14:00:00Z",
                "state": "Programada"
            }
        }
