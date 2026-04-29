"""Run the CineMatch Streamlit frontend.

This module defines the main Streamlit user interface for CineMatch. It renders
the profile sidebar, movie search, rating controls, recommendation cards, and
Graphviz recommendation graph. State changes are delegated to ``app_state.py``,
API calls to ``api_client.py``, and graph construction to ``graph.py`` so this
file stays focused on layout and user interaction.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from api_client import api_get, cached_search_movies_by_title
from app_state import (
    add_movie_to_profile,
    create_new_profile,
    delete_profile,
    get_active_profile,
    initialize_session_state,
    refresh_all_recommendations,
    remove_movie_from_profile,
    reset_graph,
    set_current_rating,
)
from config import (
    API_URL,
    MAX_RATING,
    MAX_SEARCH_RESULTS,
    MIN_RATING,
    RATING_STEP,
    TOP_K_RECOMMENDATIONS,
)
from graph import build_graph_dot

st.set_page_config(
    page_title="CineMatch",
    page_icon="🎬",
    layout="wide",
)


def inject_theme_aware_styles() -> None:
    """Inject custom CSS for theme-aware Streamlit styling."""
    st.markdown(
        """
        <style>
            .cinematch-rating-display {
                text-align: center;
                font-size: 1.9rem;
                line-height: 2.25rem;
                min-height: 3.15rem;
                border: 1px solid var(--st-border-color, rgba(128, 128, 128, 0.35));
                border-radius: 0.5rem;
                padding: 0.38rem 0.5rem;
                background: var(--st-secondary-background-color, transparent);
                color: var(--st-text-color, inherit);
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            div[data-testid="stHorizontalBlock"]:has(.cinematch-rating-display) button {
                min-height: 3.15rem;
                height: 3.15rem;
                padding-top: 0;
                padding-bottom: 0;
            }

            div[data-testid="stGraphVizChart"] svg {
                background: transparent !important;
            }

            div[data-testid="stGraphVizChart"] svg text {
                fill: var(--st-text-color, currentColor) !important;
            }

            div[data-testid="stGraphVizChart"] svg g[id^="movie_node_"] path,
            div[data-testid="stGraphVizChart"] svg g[id^="movie_node_"] polygon {
                fill: var(--st-text-color, currentColor) !important;
                filter: invert(1) contrast(2.2) brightness(1.4) !important;
                stroke: var(--st-text-color, currentColor) !important;
                stroke-width: 1.2px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_genres(movie: dict[str, Any]) -> str:
    """Format movie genres for display."""
    genres = movie.get("movie_genres", [])

    if not genres:
        return "No genres"

    return ", ".join(sorted(genres))


def format_tags(movie: dict[str, Any], max_tags: int = 6) -> str:
    """Format movie tags for display."""
    tags = movie.get("movie_tags", [])

    if not tags:
        return "No tags"

    sorted_tags = sorted(tags)
    visible_tags = sorted_tags[:max_tags]

    if len(sorted_tags) > max_tags:
        return ", ".join(visible_tags) + ", ..."

    return ", ".join(visible_tags)


def format_stars(rating: float) -> str:
    """Format a numeric rating as stars."""
    full_stars = int(rating)
    has_half_star = rating - full_stars >= 0.5
    empty_stars = int(MAX_RATING) - full_stars - int(has_half_star)

    stars = "★" * full_stars

    if has_half_star:
        stars += "½"

    stars += "☆" * empty_stars

    return f"{stars}  {rating:.1f}"


def render_rating_selector() -> None:
    """Render the rating selector for the currently selected movie."""
    rating = float(st.session_state.current_rating)

    minus_column, stars_column, plus_column = st.columns([1, 3, 1])

    with minus_column:
        if st.button("−", key="rating_minus", use_container_width=True):
            set_current_rating(rating - RATING_STEP)
            st.rerun()

    with stars_column:
        st.markdown(
            f"""
            <div class="cinematch-rating-display">
                {format_stars(rating)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with plus_column:
        if st.button("+", key="rating_plus", use_container_width=True):
            set_current_rating(rating + RATING_STEP)
            st.rerun()

    star_columns = st.columns(5)

    for star_index, star_column in enumerate(star_columns, start=1):
        with star_column:
            star_symbol = "★" if star_index <= int(rating) else "☆"

            if st.button(
                star_symbol,
                key=f"rating_star_{star_index}",
                use_container_width=True,
            ):
                set_current_rating(float(star_index))
                st.rerun()


def render_recommendations() -> None:
    """Render recommendation cards for the active user profile."""
    active_profile = get_active_profile()
    active_profile_name = active_profile["name"]

    st.subheader(
        f"Top {TOP_K_RECOMMENDATIONS} Recommendations for {active_profile_name}"
    )

    if not active_profile["selected_movies"]:
        st.info("Add at least one rated movie to generate recommendations.")
        return

    if st.button("Refresh all recommendations", use_container_width=False):
        refresh_all_recommendations()
        st.rerun()

    recommendations = active_profile["recommendations"][:TOP_K_RECOMMENDATIONS]

    if not recommendations:
        st.warning("No recommendations available yet.")
        return

    columns = st.columns(TOP_K_RECOMMENDATIONS)

    for column, movie in zip(columns, recommendations):
        with column:
            with st.container(border=True):
                st.markdown(f"### {movie['movie_title']}")
                st.caption(f"Movie ID: {movie['movie_id']}")
                st.write(f"**Genres:** {format_genres(movie)}")
                st.write(f"**Tags:** {format_tags(movie)}")


def render_graph() -> None:
    """Render the shared recommendation graph."""
    st.subheader("Shared Recommendation Graph")

    has_any_movie = any(
        profile["selected_movies"] for profile in st.session_state.profiles.values()
    )

    if not has_any_movie:
        st.info("The graph appears after at least one user rates a movie.")
        return

    dot = build_graph_dot()
    st.graphviz_chart(dot, use_container_width=True)


def use_default_initial_user() -> None:
    """Use the default first user if the initial user dialog is dismissed."""
    if st.session_state.get("first_user_name_set", False):
        return

    st.session_state.profiles["user_1"]["name"] = "User 1"
    st.session_state.active_profile_id = "user_1"
    st.session_state.first_user_name_set = True


@st.dialog("Create first CineMatch user", on_dismiss=use_default_initial_user)
def render_initial_user_dialog() -> None:
    """Render the dialog used to create the first user profile."""
    with st.form("initial_user_form", clear_on_submit=False):
        profile_name = st.text_input(
            "User name",
            placeholder="Example: User 1",
            key="initial_user_name",
        )

        submitted = st.form_submit_button(
            "Start",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not profile_name.strip():
            st.warning("Enter a user name.")
            return

        st.session_state.profiles["user_1"]["name"] = profile_name.strip()
        st.session_state.active_profile_id = "user_1"
        st.session_state.first_user_name_set = True
        st.rerun()


@st.dialog("Add new CineMatch user")
def render_add_user_dialog() -> None:
    """Render the dialog used to add another user profile."""
    with st.form("add_user_form", clear_on_submit=True):
        profile_name = st.text_input(
            "User name",
            placeholder="Example: User 2",
            key="new_user_name",
        )

        submitted = st.form_submit_button(
            "Create user",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not profile_name.strip():
            st.warning("Enter a user name.")
            return

        create_new_profile(profile_name)
        st.rerun()

    if st.button("Cancel", use_container_width=True):
        st.rerun()


@st.dialog("Delete user")
def render_delete_user_dialog(profile_id: str) -> None:
    """Render the confirmation dialog for deleting a user profile."""
    profile = st.session_state.profiles[profile_id]

    st.write(f'Delete "{profile["name"]}" and all rated movies for this user?')

    confirm_column, cancel_column = st.columns(2)

    with confirm_column:
        if st.button("Delete user", type="primary", use_container_width=True):
            delete_profile(profile_id)
            st.rerun()

    with cancel_column:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Reset graph")
def render_reset_graph_dialog() -> None:
    """Render the confirmation dialog for resetting the complete graph."""
    st.write(
        "Are you sure you want to reset the graph?\n\nThis will delete all users, ratings and recommendations."
    )

    confirm_column, cancel_column = st.columns(2)

    with confirm_column:
        if st.button("Reset graph", type="primary", use_container_width=True):
            reset_graph()
            st.rerun()

    with cancel_column:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_sidebar() -> None:
    """Render the sidebar with profile and rating management."""
    with st.sidebar:
        if st.button("New graph / reset all", type="primary", use_container_width=True):
            render_reset_graph_dialog()

        if st.button("Add new user", use_container_width=True):
            render_add_user_dialog()

        profile_ids = list(st.session_state.profiles.keys())
        active_profile_id = st.session_state.active_profile_id
        active_index = profile_ids.index(active_profile_id)

        selected_profile_id = st.selectbox(
            "Active user",
            options=profile_ids,
            index=active_index,
            format_func=lambda profile_id: st.session_state.profiles[profile_id][
                "name"
            ],
        )

        if selected_profile_id != active_profile_id:
            st.session_state.active_profile_id = selected_profile_id
            set_current_rating(2.5)
            st.rerun()

        active_profile = get_active_profile()
        delete_disabled = len(st.session_state.profiles) <= 1

        if st.button(
            "Delete active user",
            use_container_width=True,
            disabled=delete_disabled,
        ):
            render_delete_user_dialog(st.session_state.active_profile_id)

        st.divider()

        st.subheader("Rated Movies")

        if not active_profile["selected_movies"]:
            st.caption("No movies selected for this user yet.")
        else:
            for movie_id, movie in list(active_profile["selected_movies"].items()):
                with st.expander(movie["movie_title"], expanded=False):
                    st.caption(f"Movie ID: {movie['movie_id']}")
                    st.write(f"**Genres:** {format_genres(movie)}")
                    st.write(f"**Tags:** {format_tags(movie)}")

                    new_rating = st.slider(
                        "Rating",
                        min_value=MIN_RATING,
                        max_value=MAX_RATING,
                        value=float(movie["rating"]),
                        step=RATING_STEP,
                        key=f"sidebar_rating_{st.session_state.active_profile_id}_{movie_id}",
                    )

                    if new_rating != float(movie["rating"]):
                        active_profile["selected_movies"][movie_id]["rating"] = float(
                            new_rating
                        )
                        refresh_all_recommendations()
                        st.rerun()

                    if st.button(
                        "Remove movie",
                        key=f"remove_{st.session_state.active_profile_id}_{movie_id}",
                        use_container_width=True,
                    ):
                        remove_movie_from_profile(movie_id)
                        st.rerun()

        st.divider()

        with st.expander("Backend status", expanded=False):
            st.write(f"API URL: `{API_URL}`")

            if st.button("Check API connection", key="sidebar_backend_check"):
                version_data = api_get("/api/version")

                if version_data is not None:
                    st.success(
                        f"Backend reachable. Version: {version_data.get('version')}"
                    )


def render_movie_suggestions(
    profile_id: str,
    search_query: str,
    search_results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Render movie search suggestions and return the selected movie."""
    if not search_query.strip():
        st.caption("Start typing to search for movies.")
        return None

    if len(search_query.strip()) < 2:
        st.caption("Enter at least 2 characters.")
        return None

    if not search_results:
        st.info("No matching movies found.")
        return None

    selected_movie = st.session_state.selected_search_movie_by_profile.get(profile_id)

    if selected_movie is None:
        selected_movie = search_results[0]
        st.session_state.selected_search_movie_by_profile[profile_id] = selected_movie

    selected_movie_id = str(selected_movie["movie_id"])

    for movie in search_results[:MAX_SEARCH_RESULTS]:
        movie_id = str(movie["movie_id"])
        title = movie["movie_title"]
        genres = format_genres(movie)

        prefix = "✓ " if movie_id == selected_movie_id else ""
        button_label = f"{prefix}{title}  ·  {genres}"

        if st.button(
            button_label,
            key=f"suggestion_{profile_id}_{movie_id}",
            use_container_width=True,
        ):
            st.session_state.selected_search_movie_by_profile[profile_id] = movie
            selected_movie = movie
            st.rerun()

    if selected_movie is not None:
        with st.container(border=True):
            st.markdown(f"### {selected_movie['movie_title']}")
            st.caption(f"Movie ID: {selected_movie['movie_id']}")
            st.write(f"**Genres:** {format_genres(selected_movie)}")
            st.write(f"**Tags:** {format_tags(selected_movie)}")

    return selected_movie


def render_search_area() -> None:
    """Render movie search, rating selection, and add button."""
    active_profile = get_active_profile()
    profile_id = st.session_state.active_profile_id

    st.subheader(f"Add Movie Rating for {active_profile['name']}")

    input_column, rating_column, confirm_column = st.columns([4, 4, 0.45])

    selected_movie = None

    with input_column:
        search_query = st.text_input(
            "Search movie title",
            placeholder="Start typing a movie title...",
            label_visibility="collapsed",
            key=f"movie_search_{profile_id}",
        )

        previous_query = st.session_state.last_search_query_by_profile.get(profile_id)

        if previous_query != search_query:
            st.session_state.selected_search_movie_by_profile.pop(profile_id, None)
            st.session_state.last_search_query_by_profile[profile_id] = search_query

        search_results = cached_search_movies_by_title(search_query)

        selected_movie = render_movie_suggestions(
            profile_id=profile_id,
            search_query=search_query,
            search_results=search_results,
        )

    with rating_column:
        render_rating_selector()

    with confirm_column:
        if st.button(
            "✓",
            type="primary",
            use_container_width=True,
            disabled=selected_movie is None,
        ):
            if selected_movie is None:
                return

            add_movie_to_profile(
                selected_movie,
                float(st.session_state.current_rating),
            )
            st.session_state.selected_search_movie_by_profile.pop(profile_id, None)
            st.success("Movie added.")
            st.rerun()


def main() -> None:
    """Run the CineMatch Streamlit app."""
    initialize_session_state()
    inject_theme_aware_styles()

    if not st.session_state.first_user_name_set:
        render_initial_user_dialog()
        return

    render_sidebar()

    st.title("🎬 CineMatch")
    st.caption(
        "Build several temporary user profiles and compare their movie taste in one graph."
    )

    render_recommendations()

    st.divider()

    render_graph()

    st.divider()

    render_search_area()


if __name__ == "__main__":
    main()
