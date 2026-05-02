from sqlalchemy.orm import Session
from fastapi import HTTPException, Query
import requests, dotenv, os, json

from models.user import Users
from models.rating import Ratings
from models.movie import Movies, Movie_genres, Tags
from models.enum import Genres

from schemas.recommendation import MoviesResponse, UserMovieRatings, MoviePredictions

dotenv.load_dotenv()


def get_movies(
    db: Session, title: str, genres: list, tags: list
) -> list[MoviesResponse]:
    """Fetches movies from the database, filtered by the given args. Filter uses AND for the different params.
    The passed values are not validated, as this is a search function.

    Args:
        db (Session): Provided by the session factory from the router
        title (str): Movie titles
        genres (list): Movie genres
        tags (list): Tags

    Returns:
        list[MoviesResponse]: List of movies and according attributes
    """

    # build conditional query
    query = (
        db.query(
            Movies.id.label("movie_id"),
            Movies.title.label("movie_title"),
            Genres.name.label("movie_genre"),
            Tags.tag.label("movie_tag"),
        )
        .outerjoin(Tags)
        .outerjoin(Movie_genres)
        .outerjoin(Genres)
    )

    # match available criteria and add as needed
    if title:
        query = query.filter(Movies.title.ilike(f"%{title}%"))
    if genres:
        query = query.filter(Genres.name.in_(genres))
    if tags:
        query = query.filter(Tags.tag.in_(tags))

    rows: object = query.order_by(Movies.title).all()
    movies: dict = movie_row_parser(rows)

    response: list = [
        MoviesResponse(
            movie_id=v["movie_id"],
            movie_title=v["movie_title"],
            movie_genres=[g for g in v["movie_genres"] if g is not None],
            movie_tags=[t for t in v["movie_tags"] if t is not None],
        )
        for v in movies.values()
    ]

    return response


def create_movie_recommendations(
    db: Session, user_movie_ratings: list[UserMovieRatings]
) -> MoviePredictions:
    """Generates movie reccomendations, using the model-service api.

    Args:
        db (Session): Provided by the session factory from the router
        user_movie_ratings (list[UserMovieRatings]): provided user ratings, needed for the recc system

    Returns:
        MoviePredictions: Movies, with a rating prediction
    """

    # validations
    movie_ids_ui: list = [item.movie_id for item in user_movie_ratings]
    validation_movie_ids(movie_ids_ui, db)
    check_model_service_health()

    # get reccomendations from api
    body: list = [item.model_dump() for item in user_movie_ratings]
    predict_url: str = f"{os.getenv('MODEL_SERVICE_URL')}/predict"
    r = requests.post(url=predict_url, json=body)

    # parse model service response
    api_response_unparsed: dict = json.loads(r.content.decode("utf-8"))
    api_response: dict = {}
    for item in api_response_unparsed:
        api_response[item["movieId"]] = item["predictedRating"]

    # enrich movie data for final response
    query = (
        db.query(
            Movies.id.label("movie_id"),
            Movies.title.label("movie_title"),
            Genres.name.label("movie_genre"),
            Tags.tag.label("movie_tag"),
        )
        .outerjoin(Tags)
        .outerjoin(Movie_genres)
        .outerjoin(Genres)
    ).filter(Movies.id.in_(list(api_response.keys())))

    rows = query.order_by(Movies.id).all()
    movies: dict = movie_row_parser(rows)

    response: list = [
        MoviePredictions(
            movie_id=v["movie_id"],
            movie_title=v["movie_title"],
            movie_genres=[g for g in v["movie_genres"] if g is not None],
            movie_tags=[t for t in v["movie_tags"] if t is not None],
            predicted_rating=api_response[int(v["movie_id"])],
        )
        for v in movies.values()
    ]

    return response


########################## validation and utility funcitons ##########################


def movie_row_parser(rows: object) -> dict:
    """Parses the given row-itterable from SQLAlchemy to a python dict.

    Args:
        rows (object): SQLAlchemy itterable

    Returns:
        dict: {"movie_id": 1, "movie_title": "title", movie_genres: ["genre1",], movie_tags: ["tag1", ...]}
    """

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

    return movies


def check_model_service_health() -> None:
    """Checks if the model-service is reachable and working correctly

    Raises:
        HTTPException: 500 if not reachable
        HTTPException: 500 if not working as intended
    """

    health_url: str = f"{os.getenv('MODEL_SERVICE_URL')}/health"
    r = requests.get(health_url)

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail="Model service not reachable")

    response: dict = json.loads(r.content.decode("utf-8"))
    if response["status"] != "ok":
        raise HTTPException(status_code=500, detail="Model service health check failed")


def validation_movie_ids(movie_ids: list[int], db: Session) -> None:
    """Validates, if the given movie_ids exists in the database, and thus in the reccomendation system.

    Args:
        movie_ids (list[int]): List of movie ids
        db (Session): DB session, forward from router to not open a new one

    Raises:
        HTTPException: 422 if one or more ids are not in the system
    """

    movie_ids_ui: list = list(set(movie_ids))

    query = (
        db.query(Movies.id.label("movie_id"))
        .filter(Movies.id.in_(movie_ids_ui))
        .distinct()
    )
    rows: object = query.all()

    movie_ids_db: list = [int(r.movie_id) for r in rows]
    nok_movie_ids: list = []

    for id in movie_ids_ui:
        if id not in movie_ids_db:
            nok_movie_ids.append(id)

    if len(nok_movie_ids) > 0:
        raise HTTPException(
            status_code=422,
            detail=f"The following movie_ids do not exists: {nok_movie_ids}",
        )


def validation_require_one(
    title: str | None = Query(default=None),
    genres: list | None = Query(default=None),
    tags: list | None = Query(default=None),
) -> dict:
    """Validation function, called by the GET /movies router to check if at least one search param was given.

    Args:
        title (str | None, optional): Defaults to Query(default=None).
        genres (list | None, optional): Defaults to Query(default=None).
        tags (list | None, optional): Defaults to Query(default=None).

    Raises:
        HTTPException: 422 if not at least one param was passed

    Returns:
        dict: returns the sorted query params as a dict: {"title": title, "genres": genres, "tags": tags}
    """

    if not any([title, genres, tags]):
        raise HTTPException(
            status_code=422, detail="At least one query parameter must be provided."
        )
    return {"title": title, "genres": genres, "tags": tags}
