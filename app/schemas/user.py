from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    email: str
    password: str

    class Config:
        orm_mode = True

class RegisterRequest(BaseModel):
    email: str
    password: str

