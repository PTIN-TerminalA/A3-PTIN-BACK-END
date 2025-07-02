from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Ticket(Base):
    __tablename__ = "ticket"

    flight_id = Column(Integer, ForeignKey("flight.id"), primary_key=True)
    user_id = Column(Integer, primary_key=True)
    class_type = Column(String, name="class")  # 'class' es palabra reservada, usamos alias
    seat = Column(String)
    number = Column(String)
    qr_code_link = Column(String)

    flight = relationship("Flight", back_populates="tickets")
