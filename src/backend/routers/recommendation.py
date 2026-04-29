from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from schemas.recommendation import *
from services import recommendation as recommendation_service

# from services.user_service import get_user, list_users
from database import get_db

router = APIRouter()


@router.get("/movies", response_model=list[MoviesResponse])
def get_movies(
    params: dict = Depends(recommendation_service.validation_require_one),
    db: Session = Depends(get_db),
):
    response: list[MoviesResponse] = recommendation_service.get_movies(
        title=params["title"], genres=params["genres"], tags=params["tags"], db=db
    )
    return response


@router.post("/create_movie_recommendations", response_model=list[MoviePredictions])
def create_movie_rcommendations(
    user_movie_ratings: list[UserMovieRatings], db: Session = Depends(get_db)
):
    response: list[MoviePredictions] = (
        recommendation_service.create_movie_recommendations(
            db=db, user_movie_ratings=user_movie_ratings
        )
    )
    return response
