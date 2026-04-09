from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base


class Genres(Base):
    __tablename__ = "genres"
    __table_args__ = {"schema": "enum"}

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    movie_genres = relationship("Movie_genres", back_populates="genres")
