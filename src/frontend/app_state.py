"""Manage Streamlit session state for user profiles and recommendations.

This module contains the state management logic for the CineMatch frontend. It
initializes the Streamlit session state, manages user profiles, stores selected
movie ratings, resets UI-related state, and refreshes recommendations through
the backend API.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from api_client import api_post
from config import (
    MAX_RATING,
    MIN_RATING,
    RATING_STEP,
    TOP_K_GRAPH_RECOMMENDATIONS,
)


def normalize_rating(rating: float) -> float:
    """Normalize a rating to the configured rating scale.

    Parameters
    ----------
    rating:
        Raw rating value.

    Returns
    -------
    float
        Rating clipped to the allowed range and rounded to the rating step.
    """
    rating = round(float(rating) / RATING_STEP) * RATING_STEP
    rating = max(MIN_RATING, min(MAX_RATING, rating))
    return float(rating)


def set_current_rating(rating: float) -> None:
    """Store the current rating in the Streamlit session state.

    Parameters
    ----------
    rating:
        New raw rating value.
    """
    st.session_state.current_rating = normalize_rating(rating)


def clear_ui_state() -> None:
    """Clear temporary UI state from the Streamlit session state.

    This removes widget keys related to profile names, movie searches, selected
    movies, sidebar ratings, and suggestions. Persistent profile data is not
    removed here.
    """
    prefixes_to_clear = (
        "profile_name_",
        "movie_search_",
        "movie_select_",
        "sidebar_rating_",
        "suggestion_",
        "new_user_name",
        "initial_user_name",
    )

    for key in list(st.session_state.keys()):
        if key.startswith(prefixes_to_clear):
            del st.session_state[key]

    st.session_state.selected_search_movie_by_profile = {}
    st.session_state.last_search_query_by_profile = {}


def initialize_session_state() -> None:
    """Initialize all required Streamlit session state values.

    Existing values are preserved. Missing values are created with their default
    state so the rest of the frontend can safely access them.
    """
    if "profile_counter" not in st.session_state:
        st.session_state.profile_counter = 1

    if "profiles" not in st.session_state:
        st.session_state.profiles = {
            "user_1": {
                "name": "User 1",
                "selected_movies": {},
                "recommendations": [],
            }
        }

    if "active_profile_id" not in st.session_state:
        st.session_state.active_profile_id = "user_1"

    if "current_rating" not in st.session_state:
        st.session_state.current_rating = 2.5

    if "selected_search_movie_by_profile" not in st.session_state:
        st.session_state.selected_search_movie_by_profile = {}

    if "last_search_query_by_profile" not in st.session_state:
        st.session_state.last_search_query_by_profile = {}

    if "first_user_name_set" not in st.session_state:
        st.session_state.first_user_name_set = False


def get_active_profile() -> dict[str, Any]:
    """Return the currently active user profile.

    Returns
    -------
    dict[str, Any]
        Active profile dictionary from the Streamlit session state.
    """
    return st.session_state.profiles[st.session_state.active_profile_id]


def reset_graph() -> None:
    """Reset the complete profile and recommendation state.

    This clears temporary UI state, restores the default profile, resets the
    active profile, and sets the current rating back to the default value.
    """
    clear_ui_state()

    st.session_state.pop("collapsed_graph_genres", None)
    st.session_state.pop("visible_graph_genres", None)
    st.session_state.pop("graph_genre_movie_counts", None)

    st.session_state.profile_counter = 1
    st.session_state.profiles = {
        "user_1": {
            "name": "User 1",
            "selected_movies": {},
            "recommendations": [],
        }
    }
    st.session_state.active_profile_id = "user_1"
    st.session_state.first_user_name_set = False
    set_current_rating(2.5)


def create_new_profile(profile_name: str) -> None:
    """Create a new user profile and make it active.

    Parameters
    ----------
    profile_name:
        Desired display name for the new profile.
    """
    st.session_state.profile_counter += 1

    profile_id = f"user_{st.session_state.profile_counter}"
    clean_profile_name = profile_name.strip()

    if not clean_profile_name:
        clean_profile_name = f"User {st.session_state.profile_counter}"

    st.session_state.profiles[profile_id] = {
        "name": clean_profile_name,
        "selected_movies": {},
        "recommendations": [],
    }

    st.session_state.active_profile_id = profile_id
    set_current_rating(2.5)


def delete_profile(profile_id: str) -> None:
    """Delete a user profile from the session state.

    Parameters
    ----------
    profile_id:
        ID of the profile that should be deleted.
    """
    if len(st.session_state.profiles) <= 1:
        reset_graph()
        return

    st.session_state.profiles.pop(profile_id, None)
    st.session_state.selected_search_movie_by_profile.pop(profile_id, None)
    st.session_state.last_search_query_by_profile.pop(profile_id, None)

    remaining_profile_ids = list(st.session_state.profiles.keys())

    if st.session_state.active_profile_id == profile_id:
        st.session_state.active_profile_id = remaining_profile_ids[0]

    set_current_rating(2.5)
    refresh_all_recommendations()


def rating_to_payload(profile_id: str | None = None) -> list[dict[str, float | int]]:
    """Convert selected movie ratings into a backend payload.

    Parameters
    ----------
    profile_id:
        Optional profile ID. If omitted, the active profile is used.

    Returns
    -------
    list[dict[str, float | int]]
        List of movie IDs and ratings expected by the recommendation API.
    """
    if profile_id is None:
        profile_id = st.session_state.active_profile_id

    profile = st.session_state.profiles[profile_id]

    return [
        {
            "movie_id": int(movie["movie_id"]),
            "rating": float(movie["rating"]),
        }
        for movie in profile["selected_movies"].values()
    ]


def refresh_recommendations(profile_id: str | None = None) -> None:
    """Refresh recommendations for one profile.

    Parameters
    ----------
    profile_id:
        Optional profile ID. If omitted, the active profile is used.
    """
    if profile_id is None:
        profile_id = st.session_state.active_profile_id

    profile = st.session_state.profiles[profile_id]
    payload = rating_to_payload(profile_id)

    if not payload:
        profile["recommendations"] = []
        return

    recommendations = api_post(
        "/api/recommendation/create_movie_recommendations",
        json_data=payload,
    )

    if recommendations is None:
        return

    selected_movie_ids = {
        int(movie["movie_id"]) for movie in profile["selected_movies"].values()
    }

    filtered_recommendations = [
        movie
        for movie in recommendations
        if int(movie["movie_id"]) not in selected_movie_ids
    ]

    profile["recommendations"] = filtered_recommendations[:TOP_K_GRAPH_RECOMMENDATIONS]


def refresh_all_recommendations() -> None:
    """Refresh recommendations for all existing profiles."""
    for profile_id, profile in st.session_state.profiles.items():
        if profile["selected_movies"]:
            refresh_recommendations(profile_id)
        else:
            profile["recommendations"] = []


def add_movie_to_profile(movie: dict[str, Any], rating: float) -> None:
    """Add a movie rating to the active profile.

    Parameters
    ----------
    movie:
        Movie record returned by the backend.
    rating:
        Rating assigned to the movie.
    """
    active_profile = get_active_profile()
    movie_id = str(movie["movie_id"])

    active_profile["selected_movies"][movie_id] = {
        **movie,
        "rating": float(rating),
    }

    refresh_all_recommendations()


def remove_movie_from_profile(movie_id: str) -> None:
    """Remove a selected movie from the active profile.

    Parameters
    ----------
    movie_id:
        ID of the movie that should be removed.
    """
    active_profile = get_active_profile()
    active_profile["selected_movies"].pop(movie_id, None)
    refresh_all_recommendations()
