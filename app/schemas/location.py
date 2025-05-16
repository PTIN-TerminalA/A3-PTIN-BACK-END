from pydantic import BaseModel
from typing import List

class LocationSchema(BaseModel):
    x: float
    y: float
    class Config:
        orm_mode = True

class WifiMeasure(BaseModel):
    bssid: str
    rssi: float

class WifiMeasuresList(BaseModel):
    measure: List[WifiMeasure]
