from sqlalchemy import Column, Integer, String, Boolean, Time, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Flight(Base):
    __tablename__ = "flight"

    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String)
    date = Column(Date)
    departure_time = Column(Time)
    arrival_time = Column(Time)
    is_canceled = Column(Boolean)
    is_delayed = Column(Boolean)
    distance = Column(Float)
    duration = Column(Time)
    airline_id = Column(Integer, ForeignKey("airline.id"))
    boarding_time = Column(Time)
    origin_code = Column(String)
    origin_name = Column(String)
    destination_code = Column(String)

    airline = relationship("Airline", back_populates="flights")
    tickets = relationship("Ticket", back_populates="flight")
