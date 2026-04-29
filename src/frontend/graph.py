"""Build the Graphviz graph for the CineMatch frontend.

This module contains the graph construction logic used to visualize users,
selected movies, recommendations, genres, and profile compatibility. It keeps
the DOT generation separate from the Streamlit layout code so ``main.py`` only
has to render the finished graph.
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import streamlit as st

from config import TOP_K_RECOMMENDATIONS


def dot_escape(text: str) -> str:
    """Escape text for safe use in Graphviz DOT labels.

    Parameters
    ----------
    text:
        Text value that should be inserted into a DOT label.

    Returns
    -------
    str
        Escaped text without line breaks.
    """
    return str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def build_user_genre_vector(profile: dict[str, Any]) -> dict[str, float]:
    """Build a rating-weighted genre vector for one profile.

    Parameters
    ----------
    profile:
        User profile containing selected movies and ratings.

    Returns
    -------
    dict[str, float]
        Mapping from genre names to accumulated rating weights.
    """
    genre_vector: dict[str, float] = {}

    for movie in profile["selected_movies"].values():
        rating = float(movie["rating"])

        for genre in movie.get("movie_genres", []):
            genre_vector[genre] = genre_vector.get(genre, 0.0) + rating

    return genre_vector


def calculate_user_similarity(
    profile_a: dict[str, Any], profile_b: dict[str, Any]
) -> float:
    """Calculate cosine similarity between two user genre vectors.

    Parameters
    ----------
    profile_a:
        First user profile.
    profile_b:
        Second user profile.

    Returns
    -------
    float
        Cosine similarity between both profiles.
    """
    vector_a = build_user_genre_vector(profile_a)
    vector_b = build_user_genre_vector(profile_b)

    if not vector_a or not vector_b:
        return 0.0

    common_genres = set(vector_a) & set(vector_b)

    numerator = sum(vector_a[genre] * vector_b[genre] for genre in common_genres)
    norm_a = math.sqrt(sum(value**2 for value in vector_a.values()))
    norm_b = math.sqrt(sum(value**2 for value in vector_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return numerator / (norm_a * norm_b)


def get_primary_genre(movie: dict[str, Any]) -> str:
    """Return the first genre of a movie.

    Parameters
    ----------
    movie:
        Movie record with optional genre information.

    Returns
    -------
    str
        Primary genre, or ``"Unknown"`` if no genre is available.
    """
    genres = movie.get("movie_genres", [])

    if not genres:
        return "Unknown"

    return genres[0]


def get_genre_color(genre: str) -> str:
    """Return the graph color assigned to a genre.

    Parameters
    ----------
    genre:
        Genre name.

    Returns
    -------
    str
        Hex color used for graph styling.
    """
    genre_colors = {
        "Action": "#EF4444",
        "Adventure": "#F59E0B",
        "Animation": "#3B82F6",
        "Children": "#22C55E",
        "Comedy": "#EC4899",
        "Crime": "#8B5CF6",
        "Documentary": "#14B8A6",
        "Drama": "#A855F7",
        "Fantasy": "#64748B",
        "Film-Noir": "#6B7280",
        "Horror": "#DC2626",
        "Musical": "#10B981",
        "Mystery": "#7C3AED",
        "Romance": "#F43F5E",
        "Sci-Fi": "#2563EB",
        "Thriller": "#EA580C",
        "War": "#B91C1C",
        "Western": "#D97706",
        "Unknown": "#94A3B8",
    }

    return genre_colors.get(genre, "#94A3B8")


def get_genre_fill_color(genre: str) -> str:
    """Return the transparent fill color assigned to a genre.

    Parameters
    ----------
    genre:
        Genre name.

    Returns
    -------
    str
        Hex color with alpha channel for Graphviz fill styling.
    """
    return f"{get_genre_color(genre)}22"


def collect_graph_movies() -> dict[str, dict[str, Any]]:
    """Collect all movies that should appear in the graph.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapping from movie IDs to selected or recommended movie records.
    """
    movies: dict[str, dict[str, Any]] = {}

    for profile in st.session_state.profiles.values():
        for movie_id, movie in profile["selected_movies"].items():
            movies[movie_id] = movie

        for movie in profile["recommendations"][:TOP_K_RECOMMENDATIONS]:
            movie_id = str(movie["movie_id"])

            if movie_id not in movies:
                movies[movie_id] = movie

    return movies


def build_movie_node_label(movie: dict[str, Any]) -> str:
    """Build the DOT label for a movie node.

    Parameters
    ----------
    movie:
        Movie record used for the graph node.

    Returns
    -------
    str
        Escaped movie label containing title and visible genres.
    """
    title = dot_escape(movie["movie_title"])
    genres = movie.get("movie_genres", [])

    if not genres:
        return title

    visible_genres = " · ".join(genres[:3])

    if len(genres) > 3:
        visible_genres += " · ..."

    return f"{title}\\n{dot_escape(visible_genres)}"


def build_graph_dot() -> str:
    """Build the complete Graphviz DOT representation.

    Returns
    -------
    str
        DOT graph string containing profiles, movies, recommendations, genre
        clusters, ratings, and compatibility edges.
    """
    profiles = st.session_state.profiles
    active_profile_id = st.session_state.active_profile_id
    all_movies = collect_graph_movies()

    movie_ids_by_genre: dict[str, list[str]] = {}

    for movie_id, movie in all_movies.items():
        primary_genre = get_primary_genre(movie)

        if primary_genre not in movie_ids_by_genre:
            movie_ids_by_genre[primary_genre] = []

        movie_ids_by_genre[primary_genre].append(movie_id)

    lines = [
        "digraph G {",
        '  graph [rankdir="LR", bgcolor="transparent", overlap=false, splines=true, compound=true];',
        '  node [shape=box, style="rounded,filled", fillcolor="transparent", color="#888888", fontname="Arial"];',
        '  edge [color="#888888", fontname="Arial"];',
    ]

    for profile_id, profile in profiles.items():
        if profile_id == active_profile_id:
            fillcolor = "#2563EB66"
            border_color = "#2563EB"
            pen_width = "2.8"
        else:
            fillcolor = "#2563EB22"
            border_color = "#60A5FA"
            pen_width = "1.5"

        lines.append(
            f'  {profile_id} [label="{dot_escape(profile["name"])}", '
            f'shape=oval, style="filled", fillcolor="{fillcolor}", '
            f'color="{border_color}", penwidth={pen_width}];'
        )

    for cluster_index, genre in enumerate(sorted(movie_ids_by_genre.keys())):
        cluster_id = f"cluster_{cluster_index}"
        cluster_color = get_genre_color(genre)
        cluster_fill_color = get_genre_fill_color(genre)

        lines.append(f"  subgraph {cluster_id} {{")
        lines.append(f'    label="{dot_escape(genre)}";')
        lines.append(f'    color="{cluster_color}";')
        lines.append(f'    fillcolor="{cluster_fill_color}";')
        lines.append('    style="rounded,filled";')
        lines.append("    penwidth=1.5;")

        for movie_id in sorted(movie_ids_by_genre[genre]):
            movie = all_movies[movie_id]
            node_id = f"movie_{movie_id}"
            label = build_movie_node_label(movie)

            lines.append(
                f'    {node_id} [label="{label}", '
                f'id="movie_node_{movie_id}", '
                f'style="rounded,filled", fillcolor="transparent", color="#888888"];'
            )

        lines.append("  }")

    for profile_id, profile in profiles.items():
        for movie_id, movie in profile["selected_movies"].items():
            rating = float(movie["rating"])

            lines.append(
                f"  {profile_id} -> movie_{movie_id} "
                f'[label="{rating:.1f}", color="#64748B", penwidth=1.9];'
            )

    for profile_id, profile in profiles.items():
        selected_movie_ids = {
            str(movie["movie_id"]) for movie in profile["selected_movies"].values()
        }

        for movie in profile["recommendations"][:TOP_K_RECOMMENDATIONS]:
            movie_id = str(movie["movie_id"])

            if movie_id in selected_movie_ids:
                continue

            lines.append(
                f"  {profile_id} -> movie_{movie_id} "
                f'[label="rec", style=dashed, color="#22C55E", penwidth=1.8];'
            )

    for profile_id_a, profile_id_b in itertools.combinations(profiles.keys(), 2):
        similarity = calculate_user_similarity(
            profiles[profile_id_a],
            profiles[profile_id_b],
        )

        if similarity <= 0.0:
            continue

        lines.append(
            f"  {profile_id_a} -> {profile_id_b} "
            f'[dir=none, style=dashed, color="#3B82F6", penwidth=1.8, '
            f'label="compat {similarity * 100:.0f}%"];'
        )

    lines.append("}")

    return "\n".join(lines)
