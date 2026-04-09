from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from database import Base


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {"users"}

    id = Column(Integer, primary_key=True)

    tags = relationship("Tags", back_populates="users")
    ratings = relationship("Ratings", back_populates="users")
