from pydantic import BaseModel
from typing import Optional, List


class VersionResponse(BaseModel):
    version: float


class GetMoviesResponse(BaseModel):
    movie_id: int
    movie_title: str
    movie_genres: List[str]
    movie_tags: List[str]
