from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime

class ReservaProgramadaCreate(BaseModel):
    user_id: str
    start_point: Literal[
        "Porta A3", "Pàrquing", "McDonald's", "Starbucks", "Porta A2", "Serveis 1", "FCB Store", "Farmàcia",
        "Porta A1", "Punt Info. 2", "H&M", "Cafè", "Serveis 2", "Porta A4", "VIP A4", "Reclamació equipatge",
        "Control Seguretat", "Punt Info. 1", "Zona Check-in", "Levi's", "Parada Taxi"
    ]
    end_point: Literal[
        "Porta A3", "Pàrquing", "McDonald's", "Starbucks", "Porta A2", "Serveis 1", "FCB Store", "Farmàcia",
        "Porta A1", "Punt Info. 2", "H&M", "Cafè", "Serveis 2", "Porta A4", "VIP A4", "Reclamació equipatge",
        "Control Seguretat", "Punt Info. 1", "Zona Check-in", "Levi's", "Parada Taxi"
    ]
    start_time: datetime
    car_id: Optional[str] = None  # ✅ Se añade automáticamente en el backend
