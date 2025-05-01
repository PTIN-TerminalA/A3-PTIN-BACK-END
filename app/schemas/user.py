from pydantic import BaseModel, constr, Field
from datetime import date
from enum import Enum

class GenderEnum(str, Enum):
    female = "female"
    male = "male"
    other = "other"
    rather_not_to_say = "rather_not_to_say"

class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True

class RegisterRequest(BaseModel):
    name: str
    dni: str 
    email: str
    password: str
    usertype: int

class UserResponse(BaseModel):
    id: int
    name: str
    dni: str
    email: str
    password: str
    usertype: int

    class Config:
        orm_mode = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class TokenResponseGoogle(BaseModel):
    access_token: str
    token_type: str
    needs_regular: bool

class ProfileUpdateRequest(BaseModel):
    name: constr(min_length=1)
    birth_date: date
    phone_num: constr(min_length=7)
    identity: GenderEnum = Field(..., description="female|male|other|rather_not_to_say")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "name": "Joan Garcia López",
                "birth_date": "1990-05-17",
                "phone_num": "612345678",
                "identity": "male"
            }
        }
