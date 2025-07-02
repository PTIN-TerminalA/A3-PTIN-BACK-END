from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class Airline(Base):
    __tablename__ = "airline"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image = Column(String)

    flights = relationship("Flight", back_populates="airline")
