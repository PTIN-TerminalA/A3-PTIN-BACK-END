from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base  # O como hayas llamado a tu Base declarativa

class Regular(Base):
    __tablename__ = "regular"

    id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    birth_date = Column(Date, nullable=False)
    phone_num = Column(String(20), nullable=False)
    identity = Column(String(50), ForeignKey("gender.identity"), nullable=False)

    user = relationship("User")  # Opcional, por si quieres acceso a los datos del user
