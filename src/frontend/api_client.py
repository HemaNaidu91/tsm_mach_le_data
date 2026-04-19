"""Provide backend API access helpers for the Streamlit frontend.

This module contains the small HTTP wrapper functions used by the Streamlit
frontend to communicate with the backend service. It keeps request handling,
timeouts, JSON decoding, caching, and basic error handling in one place instead
of spreading API logic across the main application file.

The generic helper functions return decoded JSON data on success and ``None`` on
failure. The cached movie search returns an empty list on failure, because search
suggestions should fail quietly while the user is typing.
"""

from typing import Any

import requests
import streamlit as st

from config import API_URL


def api_get(
    endpoint: str, params: list[tuple[str, str]] | dict[str, Any] | None = None
) -> Any | None:
    """Send a GET request to the backend API.

    Parameters
    ----------
    endpoint:
        Relative backend endpoint.
    params:
        Optional query parameters.

    Returns
    -------
    Any | None
        Decoded JSON response, or ``None`` if the request fails.
    """
    url = f"{API_URL}{endpoint}"

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as error:
        st.error(f"API request failed: {error}")
        return None


def api_post(endpoint: str, json_data: Any | None = None) -> Any | None:
    """Send a POST request to the backend API.

    Parameters
    ----------
    endpoint:
        Relative backend endpoint.
    json_data:
        Optional JSON payload.

    Returns
    -------
    Any | None
        Decoded JSON response, or ``None`` if the request fails.
    """
    url = f"{API_URL}{endpoint}"

    try:
        response = requests.post(url, json=json_data, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as error:
        st.error(f"API request failed: {error}")
        return None


@st.cache_data(ttl=30, show_spinner=False)
def cached_search_movies_by_title(title: str) -> list[dict[str, Any]]:
    """Search movies by title with short-term Streamlit caching.

    Parameters
    ----------
    title:
        Movie title or partial movie title.

    Returns
    -------
    list[dict[str, Any]]
        Matching movie records, or an empty list if no request is sent.
    """
    title = title.strip()

    if len(title) < 2:
        return []

    url = f"{API_URL}/api/recommendation/movies"

    try:
        response = requests.get(
            url,
            params=[("title", title)],
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException:
        return []
