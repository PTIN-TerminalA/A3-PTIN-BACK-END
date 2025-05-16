from sqlalchemy import Column, Integer, String, Text, DECIMAL
from app.database import Base

class Service(Base):
    __tablename__ = 'service'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    link = Column(String(255), nullable=False)
    ad_path = Column(String(255), nullable=False)
    avg_price = Column(Integer, nullable=False, index=True)
    location_x = Column(DECIMAL(5, 4), nullable=False)
    location_y = Column(DECIMAL(5, 4), nullable=False)
    status = Column(String(6), nullable=False, default='closed')
    offer = Column(String(100), nullable=True)
