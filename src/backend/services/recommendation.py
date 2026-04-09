from sqlalchemy.orm import Session
from fastapi import HTTPException

# from models.user import User


def get_movies(db: Session, title: str, genres: list, tags: list):

    if (title is None) and (genres is None) and (tags is None):
        print("exception raised")
        raise HTTPException(
            status_code=403, detail="At least one query parameter must be provided"
        )

    return {"some": "params"}


"""
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session):
    return db.query(User).all()
"""
