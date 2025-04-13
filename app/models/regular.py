from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Regular(Base):
    __tablename__ = 'regular'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'))  # Relación con el modelo User

    name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone_num = Column(String(20), nullable=False)  # Cambié a 'phone_num' como en tu tabla
    identity = Column(String(50), nullable=False)  # Cambié a 'identity' como en tu tabla

    # Relación con el modelo User
    user = relationship("User", back_populates="regular")
