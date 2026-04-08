from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services.user_service import get_user, list_users
from database import get_db
from schemas.user_schema import UserRead

router = APIRouter()


@router.get("/", response_model=list[UserRead])
def read_users(db: Session = Depends(get_db)):
    return list_users(db)  # Pass db session to the service


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return get_user(db, user_id)
