from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from routers.schemas import GetMoviesResponse
from services import recommendation as recommendation_service

# from services.user_service import get_user, list_users
from database import get_db

router = APIRouter()


@router.get(
    "/movies", response_model=list[GetMoviesResponse]
)  # response_model=list[None])
def get_movies(
    title: Optional[str] = None,
    genres: Optional[List] = Query(None),
    tags: Optional[List] = Query(None),
    db: Session = Depends(get_db),
):

    print("TITLE: ", title)
    print("GENRE: ", genres)
    print("TAGS: ", tags)
    response: dict = recommendation_service.get_movies(
        title=title, genres=genres, tags=tags, db=db
    )
    return [
        {
            "movie_id": 418,
            "movie_title": "some_title",
            "movie_genres": ["gen1", "gen2"],
            "movie_tags": ["tag1", "tag2"],
        }
    ]


"""
@router.get("/", response_model=list[UserRead])
def read_users(db: Session = Depends(get_db)):
    return list_users(db)  # Pass db session to the service


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return get_user(db, user_id)
"""
