from pydantic import BaseModel

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
    access_token:str
    token_type: str