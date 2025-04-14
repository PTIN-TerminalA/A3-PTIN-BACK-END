from pydantic import BaseModel
from datetime import date

class RegularCreate(BaseModel):
    email: str
    name: str
    birth_date: date
    phone_num: str  # Cambié a 'phone_num' como en tu tabla
    identity: str

    class Config:
        orm_mode = True  # Esto permite que Pydantic pueda trabajar con SQLAlchemy
