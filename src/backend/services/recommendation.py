from sqlalchemy.orm import Session
from fastapi import HTTPException, Query

from models.user import Users
from models.rating import Ratings
from models.movie import Movies, Movie_genres, Tags
from models.enum import Genres

from schemas.recommendation import MoviesResponse


def get_movies(
    db: Session, title: str, genres: list, tags: list
) -> list[MoviesResponse]:

    # prevent from loading all movies
    if (title is None) and (genres is None) and (tags is None):
        print("exception raised")
        raise HTTPException(
            status_code=403, detail="At least one query parameter must be provided"
        )

    # build conditional query
    query = (
        db.query(
            Movies.id.label("movie_id"),
            Movies.title.label("movie_title"),
            Genres.name.label("movie_genre"),
            Tags.tag.label("movie_tag"),
        )
        .join(Tags)
        .join(Movie_genres)
        .join(Genres)
    )

    # match available criteria and add as needed
    if title:
        query = query.filter(Movies.title.ilike(f"%{title}%"))
    if genres:
        query = query.filter(Genres.name.in_(genres))
    if tags:
        query = query.filter(Tags.tag.in_(tags))

    rows: object = query.order_by(Movies.title).all()
    movies: dict = {}

    for r in rows:

        if r.movie_id not in movies:

            movies[r.movie_id] = {
                "movie_id": r.movie_id,
                "movie_title": r.movie_title,
                "movie_genres": set(),
                "movie_tags": set(),
            }

        movies[r.movie_id]["movie_genres"].add(
            r.movie_genre
        )  # using set to prevent duplicat genres
        movies[r.movie_id]["movie_tags"].add(
            r.movie_tag
        )  # using set to prevent duplicat tags

    response: list = [
        MoviesResponse(
            movie_id=v["movie_id"],
            movie_title=v["movie_title"],
            movie_genres=list(v["movie_genres"]),
            movie_tags=list(v["movie_tags"]),
        )
        for v in movies.values()
    ]

    return response


def create_movie_recommendations(db: Session):

    # TODO: Implement model correctly
    # NOTE: This is just a placeholder, so the function returns something

    import random
    import string

    letter: str = random.choice(string.ascii_letters)
    size: int = random.choice([2, 3, 4])
    movies: list = get_movies(db=db, title=letter, genres=None, tags=None)

    return movies[:size]


def validation_require_one(
    title: str | None = Query(default=None),
    genres: list | None = Query(default=None),
    tags: list | None = Query(default=None),
) -> dict:
    if not any([title, genres, tags]):
        raise HTTPException(
            status_code=422, detail="At least one query parameter must be provided."
        )
    return {"title": title, "genres": genres, "tags": tags}
