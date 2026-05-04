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

from config import TOP_K_GRAPH_RECOMMENDATIONS


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
            movies[str(movie_id)] = movie

        for movie in profile["recommendations"][:TOP_K_GRAPH_RECOMMENDATIONS]:
            movie_id = str(movie["movie_id"])

            if movie_id not in movies:
                movies[movie_id] = movie

    return movies


def collect_graph_genre_counts() -> dict[str, int]:
    """Collect the number of graph movies per primary genre.

    Returns
    -------
    dict[str, int]
        Mapping from genre name to number of visible graph movies.
    """
    all_movies = collect_graph_movies()
    genre_counts: dict[str, int] = {}

    for movie in all_movies.values():
        genre = get_primary_genre(movie)
        genre_counts[genre] = genre_counts.get(genre, 0) + 1

    return dict(sorted(genre_counts.items()))


def collect_graph_genres() -> list[str]:
    """Collect all primary genres currently visible in the graph.

    Returns
    -------
    list[str]
        Sorted list of primary genres used in the graph.
    """
    return list(collect_graph_genre_counts().keys())


def sync_collapsed_graph_genres(graph_genre_counts: dict[str, int]) -> set[str]:
    """Synchronize collapsed genre state with currently visible graph genres.

    New genres are automatically collapsed if they contain more than three
    visible graph movies. Genres with one to three movies are initially
    expanded, but can still be collapsed manually with the genre buttons.

    Parameters
    ----------
    graph_genre_counts:
        Mapping from genre name to number of visible graph movies.

    Returns
    -------
    set[str]
        Currently collapsed genres.
    """
    current_genres = set(graph_genre_counts.keys())
    previous_counts = st.session_state.get("graph_genre_movie_counts", {})

    if "collapsed_graph_genres" not in st.session_state:
        collapsed_genres = {
            genre
            for genre, movie_count in graph_genre_counts.items()
            if movie_count > 3
        }
    else:
        collapsed_genres = set(st.session_state.collapsed_graph_genres)
        collapsed_genres = collapsed_genres & current_genres

        for genre, movie_count in graph_genre_counts.items():
            previous_movie_count = previous_counts.get(genre)

            if previous_movie_count is None and movie_count > 3:
                collapsed_genres.add(genre)

            elif (
                previous_movie_count is not None
                and previous_movie_count <= 3 < movie_count
            ):
                collapsed_genres.add(genre)

    st.session_state.collapsed_graph_genres = collapsed_genres
    st.session_state.graph_genre_movie_counts = dict(graph_genre_counts)
    st.session_state.visible_graph_genres = list(graph_genre_counts.keys())

    return collapsed_genres


def toggle_graph_genre(genre: str) -> None:
    """Toggle one graph genre between collapsed and expanded state.

    Parameters
    ----------
    genre:
        Genre name.
    """
    collapsed_genres = set(st.session_state.get("collapsed_graph_genres", set()))

    if genre in collapsed_genres:
        collapsed_genres.remove(genre)
    else:
        collapsed_genres.add(genre)

    st.session_state.collapsed_graph_genres = collapsed_genres


def count_recommendation_users_by_movie() -> dict[str, int]:
    """Count for how many profiles each movie is recommended.

    Returns
    -------
    dict[str, int]
        Mapping from movie ID to number of profiles that recommend this movie.
    """
    recommendation_counts: dict[str, int] = {}

    for profile in st.session_state.profiles.values():
        seen_movie_ids_for_profile: set[str] = set()

        for movie in profile["recommendations"][:TOP_K_GRAPH_RECOMMENDATIONS]:
            movie_id = str(movie["movie_id"])
            seen_movie_ids_for_profile.add(movie_id)

        for movie_id in seen_movie_ids_for_profile:
            recommendation_counts[movie_id] = recommendation_counts.get(movie_id, 0) + 1

    return recommendation_counts


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
    recommendation_counts = count_recommendation_users_by_movie()

    movie_ids_by_genre: dict[str, list[str]] = {}
    movie_genre_by_id: dict[str, str] = {}

    for movie_id, movie in all_movies.items():
        movie_id = str(movie_id)
        primary_genre = get_primary_genre(movie)
        movie_genre_by_id[movie_id] = primary_genre

        if primary_genre not in movie_ids_by_genre:
            movie_ids_by_genre[primary_genre] = []

        movie_ids_by_genre[primary_genre].append(movie_id)

    graph_genres = sorted(movie_ids_by_genre.keys())
    graph_genre_counts = {
        genre: len(movie_ids_by_genre[genre]) for genre in graph_genres
    }
    collapsed_genres = sync_collapsed_graph_genres(graph_genre_counts)

    genre_node_by_genre: dict[str, str] = {}
    collapsed_edge_data: dict[tuple[str, str], dict[str, Any]] = {}

    def get_collapsed_edge_data(profile_id: str, genre: str) -> dict[str, Any]:
        key = (profile_id, genre)

        if key not in collapsed_edge_data:
            collapsed_edge_data[key] = {
                "ratings": [],
                "fits": [],
                "has_shared_recommendation": False,
            }

        return collapsed_edge_data[key]

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

    for cluster_index, genre in enumerate(graph_genres):
        cluster_color = get_genre_color(genre)
        cluster_fill_color = get_genre_fill_color(genre)

        if genre in collapsed_genres:
            genre_node_id = f"genre_{cluster_index}"
            genre_node_by_genre[genre] = genre_node_id
            movie_count = len(movie_ids_by_genre[genre])

            lines.append(
                f'  {genre_node_id} [label="▶ {dot_escape(genre)}\\n{movie_count} movies", '
                f'shape=box, style="rounded,filled", '
                f'fillcolor="{cluster_fill_color}", color="{cluster_color}", '
                f"penwidth=2.0];"
            )

            continue

        cluster_id = f"cluster_{cluster_index}"
        genre_node_by_genre[genre] = cluster_id

        lines.append(f"  subgraph {cluster_id} {{")
        lines.append(f'    label="▼ {dot_escape(genre)}";')
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
            movie_id = str(movie_id)
            rating = float(movie["rating"])
            genre = movie_genre_by_id.get(movie_id, get_primary_genre(movie))

            if genre in collapsed_genres:
                edge_data = get_collapsed_edge_data(profile_id, genre)
                edge_data["ratings"].append(rating)
                continue

            lines.append(
                f"  {profile_id} -> movie_{movie_id} "
                f'[label="{rating:.1f}", color="#64748B", penwidth=1.9];'
            )

    for profile_id, profile in profiles.items():
        selected_movie_ids = {
            str(movie["movie_id"]) for movie in profile["selected_movies"].values()
        }

        for movie in profile["recommendations"][:TOP_K_GRAPH_RECOMMENDATIONS]:
            movie_id = str(movie["movie_id"])

            if movie_id in selected_movie_ids:
                continue

            predicted_rating = float(movie.get("predicted_rating", 0.0))
            fit_percent = predicted_rating / 5.0 * 100.0
            genre = movie_genre_by_id.get(movie_id, get_primary_genre(movie))
            is_shared_recommendation = recommendation_counts.get(movie_id, 0) >= 2

            if genre in collapsed_genres:
                edge_data = get_collapsed_edge_data(profile_id, genre)
                edge_data["fits"].append(fit_percent)

                if is_shared_recommendation:
                    edge_data["has_shared_recommendation"] = True

                continue

            if is_shared_recommendation:
                edge_color = "#EAB308"
            else:
                edge_color = "#22C55E"

            lines.append(
                f"  {profile_id} -> movie_{movie_id} "
                f'[label="fit {fit_percent:.0f}%", style=dashed, color="{edge_color}", penwidth=1.8];'
            )

    for (profile_id, genre), edge_data in collapsed_edge_data.items():
        genre_node_id = genre_node_by_genre[genre]

        label_parts: list[str] = []

        ratings = edge_data["ratings"]
        fits = edge_data["fits"]

        if ratings:
            average_rating = sum(ratings) / len(ratings)
            label_parts.append(f"rating {average_rating:.1f}")

        if fits:
            average_fit = sum(fits) / len(fits)
            label_parts.append(f"fit {average_fit:.0f}%")

        edge_label = "\\n".join(label_parts)

        if edge_data["has_shared_recommendation"]:
            edge_color = "#EAB308"
        elif fits:
            edge_color = "#22C55E"
        else:
            edge_color = "#64748B"

        if ratings and fits:
            edge_style = "solid"
            pen_width = "2.2"
        elif fits:
            edge_style = "dashed"
            pen_width = "1.8"
        else:
            edge_style = "solid"
            pen_width = "1.9"

        lines.append(
            f"  {profile_id} -> {genre_node_id} "
            f'[label="{edge_label}", style={edge_style}, color="{edge_color}", penwidth={pen_width}];'
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
