from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, ForeignKey("user.id"), primary_key=True)  # Relacionamos con User
    superadmin = Column(Boolean, default=True)  # Usamos un tipo booleano en SQLAlchemy

    user = relationship("User")  # Relación con User
