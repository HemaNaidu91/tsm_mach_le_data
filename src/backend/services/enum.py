from sqlalchemy.orm import Session
from schemas.enum import GenresResponse
from models.enum import Genres
from models.movie import Tags
from models.rating import Ratings


def get_movie_genres(db: Session) -> list[GenresResponse]:
    """Fetches all unqie movie genre from the database

    Args:
        db (Session): provided by the session factory from the router

    Returns:
        list[GenresResponse]: List of all available genres in the database
    """
    query = db.query(Genres.id.label("id"), Genres.name.label("name"))
    rows = query.all()
    response: list = [GenresResponse(id=row.id, name=row.name) for row in rows]

    return response


def get_movie_tags(db: Session) -> list[str]:
    """Fetchtes all unique tags from the database.
    The tags are not normalized, thus have to be filtered by the query.

    Args:
        db (Session): Provided by the session factory from the router

    Returns:
        list[str]: List of all available tags (not normalized)
    """
    query = db.query(Tags.tag.label("tag")).distinct().order_by(Tags.tag)
    rows = query.all()
    response: list = [row.tag for row in rows]

    return response


def get_ratings(db: Session) -> list[float]:
    """Fetches all possible ratings from the database [0.5:5:0.5]

    Args:
        db (Session): Provided by the session factory from the router

    Returns:
        list[float]: List of all availble rating scores: [0.5:5:0.5]
    """
    query = db.query(Ratings.rating.label("rating")).distinct().order_by(Ratings.rating)
    rows = query.all()
    response: list = [float(row.rating) for row in rows]

    return response
