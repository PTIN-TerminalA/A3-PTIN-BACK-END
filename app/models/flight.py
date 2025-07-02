from sqlalchemy import (
    Column, Integer, String, Date, Time,
    Boolean, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base

class Flight(Base):
    __tablename__ = "flight"

    id             = Column(Integer, primary_key=True, index=True)
    flight_number  = Column(String(20), nullable=False)
    date           = Column(Date,   nullable=False)
    departure_time = Column(Time,   nullable=False)
    arrival_time   = Column(Time,   nullable=False)
    is_canceled    = Column(Boolean, nullable=False, default=False)
    is_delayed     = Column(Boolean, nullable=False, default=False)
    distance       = Column(Float)
    duration       = Column(Time)      # TIME
    airline_id     = Column(Integer, ForeignKey("airline.id"), nullable=False)
    boarding_time  = Column(Time)
    origin_code    = Column(String(10),  nullable=False)
    origin_name    = Column(String(100), nullable=False)
    destination_code  = Column(String(10),  nullable=False)
    destination_name  = Column(String(100), nullable=False)

    # Relacions
    airline = relationship("Airline", back_populates="flights")
    tickets = relationship("Ticket",  back_populates="flight")
