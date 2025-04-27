from pydantic import BaseModel

# Este es el schema para la solicitud de creación de admin
class RegisterAdminRequest(BaseModel):
    token: str  # El id del usuario que será admin
    superadmin: bool  # Si es superadmin o admin normal

    class Config:
        orm_mode = True  # Esto asegura que FastAPI puede convertirlo a un modelo de base de datos

class AdminResponse(BaseModel):
    id: int
    superadmin: bool