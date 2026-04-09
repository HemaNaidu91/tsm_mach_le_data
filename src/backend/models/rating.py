from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Ratings(Base):
    __tablename__ = "ratings"
    __table_args__ = {"schema": "rating"}

    id = Column(Integer, primary_key=True)
    id_movie = Column(Integer, ForeignKey("movie.movies.id"), nullable=False)
    id_user = Column(Integer, ForeignKey("users.users.id"), nullable=False)
    rating = Column(Float, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=False), nullable=True)

    movies = relationship("Movies", back_populates="ratings")
    users = relationship("Users", back_populates="ratings")
