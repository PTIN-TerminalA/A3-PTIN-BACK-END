from sqlalchemy import Column, String
from app.database import Base  # Asegúrate de importar tu base declarativa correctamente

class Gender(Base):
    __tablename__ = "gender"

    identity = Column(String(50), primary_key=True, nullable=False)