from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas.enum import GenresResponse
from services import enum

router = APIRouter()


@router.get("/genres", response_model=list[GenresResponse])
def get_genres(db: Session = Depends(get_db)):
    return enum.get_movie_genres(db=db)


@router.get("/tags", response_model=list[str])
def get_tags(db: Session = Depends(get_db)):
    return enum.get_movie_tags(db=db)


@router.get("/ratings", response_model=list[float])
def get_ratings(db: Session = Depends(get_db)):
    return enum.get_ratings(db=db)
