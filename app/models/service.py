from sqlalchemy import Column, Integer, ForeignKey, String, Text, DECIMAL, Time
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


class Price(Base):
    __tablename__ = "price"
    avg_price = Column(Integer, primary_key=True)


class Schedule(Base):
    __tablename__ = "schedule"
    service_id = Column(Integer, ForeignKey("service.id"), primary_key=True)
    day = Column(String(10), primary_key=True)
    opening_hour = Column(Time, nullable=False)
    closing_hour = Column(Time, nullable=False)



class Valoration(Base):
    __tablename__ = "valoration"
    service_id = Column(Integer, ForeignKey("service.id"), primary_key=True)
    user_id = Column(Integer, primary_key=True)
    value = Column(DECIMAL(3, 2), nullable=False)
    description = Column(Text)

   

class Tag(Base):
    __tablename__ = "tag"
    name = Column(String(25), primary_key=True)

class ServiceTag(Base):
    __tablename__ = "service_tag"
    service_id = Column(Integer, ForeignKey("service.id"), primary_key=True)
    tag_name = Column(String(25), ForeignKey("tag.name"), primary_key=True)



