from pydantic import BaseModel, Field
from typing import Optional, List


class MoviesResponse(BaseModel):
    movie_id: int
    movie_title: str
    movie_genres: List[str] = []
    movie_tags: List[str] = []

    class Config:
        from_attributes = True


class UserMovieRatings(BaseModel):
    movie_id: int
    rating: float = Field(..., ge=0.5, le=5, multiple_of=0.5)


class MoviePredictions(BaseModel):
    movie_id: int
    movie_title: str
    movie_genres: List[str] = []
    movie_tags: List[str] = []
    predicted_rating: float = Field(..., ge=0.0, le=5)

    class Config:
        from_attributes = True
