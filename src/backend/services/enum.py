from sqlalchemy.orm import Session
from schemas.enum import GenresResponse
from models.enum import Genres
from models.movie import Tags
from models.rating import Ratings


def get_movie_genres(db: Session) -> list[GenresResponse]:

    query = db.query(Genres.id.label("id"), Genres.name.label("name"))
    rows = query.all()
    response: list = [GenresResponse(id=row.id, name=row.name) for row in rows]

    return response


def get_movie_tags(db: Session) -> list[str]:

    query = db.query(Tags.tag.label("tag")).distinct().order_by(Tags.tag)
    rows = query.all()
    response: list = [row.tag for row in rows]

    return response


def get_ratings(db: Session) -> list[float]:

    query = db.query(Ratings.rating.label("rating")).distinct().order_by(Ratings.rating)
    rows = query.all()
    response: list = [float(row.rating) for row in rows]

    return response
