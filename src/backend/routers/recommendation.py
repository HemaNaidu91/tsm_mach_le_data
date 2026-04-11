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


@router.post("/create_movie_recommendations", response_model=list[MoviesResponse])
def create_movie_rcommendations(
    user_movie_ratins: list[int], db: Session = Depends(get_db)
):
    response: list[MoviesResponse] = (
        recommendation_service.create_movie_recommendations(db=db)
    )
    return response


"""
@router.get("/", response_model=list[UserRead])
def read_users(db: Session = Depends(get_db)):
    return list_users(db)  # Pass db session to the service


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return get_user(db, user_id)
"""
