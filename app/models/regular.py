from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Regular(Base):
    __tablename__ = 'regular'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    birth_date = Column(Date)
    phone_num = Column(String)
    identity = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))

