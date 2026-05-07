from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from dotenv import load_dotenv

load_dotenv()


class RatedMovie(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    movie_id: int = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("movie_id", "movieId"),
        serialization_alias="movieId",
    )
    rating: float = Field(..., ge=0.5, le=5.0, multiple_of=0.5)


class RecommendedMovie(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    movie_id: int = Field(serialization_alias="movieId")
    predicted_rating: float = Field(serialization_alias="predictedRating")
