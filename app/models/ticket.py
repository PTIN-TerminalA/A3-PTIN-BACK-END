from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Ticket(Base):
    __tablename__ = "ticket"

    # Clau composta
    flight_id    = Column(Integer, ForeignKey("flight.id"), primary_key=True)
    user_id      = Column(Integer,                  primary_key=True)
    class_       = Column("class", String(50))      # `class` és paraula reservada
    seat         = Column(String(5),   nullable=False)
    number       = Column(String(50),  nullable=False)
    qr_code_link = Column(String(255), nullable=False)

    # Relació inversa
    flight = relationship("Flight", back_populates="tickets")
