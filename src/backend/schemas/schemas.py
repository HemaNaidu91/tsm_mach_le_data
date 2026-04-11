from pydantic import BaseModel
from typing import Optional, List


class VersionResponse(BaseModel):
    version: float

    class Config:
        from_attributes = True


class MoviesResponse(BaseModel):
    movie_id: int
    movie_title: str
    movie_genres: List[str]
    movie_tags: List[str]

    class Config:
        from_attributes = True


class UserMovieRatings(BaseModel):
    movie_id: int
    movie_rating: float
