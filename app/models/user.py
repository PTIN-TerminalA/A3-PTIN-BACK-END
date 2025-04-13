from sqlalchemy import Column, Integer, String
from app.database import Base

class User(Base):
    __tablename__ = 'user'  # Nombre de la tabla en MySQL

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # auto_increment
    email = Column(String(100), unique=True, index=True)  # UNIQUE constraint
    password = Column(String(255), nullable=False)  # NO NULL constraint
