from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Movies(Base):
    __tablename__ = "movies"
    __table_args_ = {"schema": "movie"}

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)

    links = relationship("Links", back_populates="movies")
    movie_genres = relationship("Movie_genres", back_populates="movies")
    tags = relationship("Tags", back_populates="movies")


class Links(Base):
    __tablename__ = "links"
    __table_args_ = {"schema": "movie"}

    id = Column(Integer, primary_key=True)
    id_movie = Column(Integer, ForeignKey("movie.movies.id"), nullable=False)
    imdbId = Column(String, nullable=False)
    tmdbId = Column(String, nullable=False)

    movies = relationship("Movies", back_populates="links")


class Movie_genres(Base):
    __tablename__ = "movie_genres"
    __table_args_ = {"schema": "movie"}

    id = Column(Integer, primary_key=True)
    id_movie = Column(Integer, ForeignKey("movie.movies.id"), nullable=False)
    id_genre = Column(Integer, ForeignKey("enum.genres.id"), nullable=False)

    movies = relationship("Movies", back_populates="movie_genres")
    genres = relationship("Genres", back_populates="movie_genres")


class Tags(Base):
    __tablename__ = "tags"
    __table_args_ = {"schema": "movie"}

    id = Column(Integer, primary_key=True)
    id_movie = Column(Integer, ForeignKey("movie.movies.id"), nullable=False)
    id_user = Column(Integer, ForeignKey("users.users"), nullable=False)
    tag = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=False), nullable=False)

    movies = relationship("Movies", back_populates="tags")
    users = relationship("Users", back_populates="tags")
