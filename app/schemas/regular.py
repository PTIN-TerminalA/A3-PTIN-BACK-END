from pydantic import BaseModel
from datetime import date

class RegisterRegularRequest(BaseModel):
    user_id: int
    birth_date: date
    phone_num: str
    identity: str

class RegularResponse(BaseModel):
    id: int
    birth_date: date
    phone_num: str
    identity: str

    class Config:
        orm_mode = True
