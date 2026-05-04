"""Define configuration values for the Streamlit frontend.

This module loads optional environment variables from a local ``.env`` file and
defines the constants used across the CineMatch frontend. Centralizing these
values keeps API configuration, display limits, rating limits, and default
profile values consistent across the application.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

TOP_K_RECOMMENDATION_CARDS = int(os.getenv("TOP_K_RECOMMENDATION_CARDS", "3"))
TOP_K_GRAPH_RECOMMENDATIONS = int(os.getenv("TOP_K_GRAPH_RECOMMENDATIONS", "5"))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "10"))

MIN_RATING = 0.5
MAX_RATING = 5.0
RATING_STEP = 0.5

DEFAULT_RATING = 2.5
DEFAULT_PROFILE_ID = "user_1"
DEFAULT_PROFILE_NAME = "User 1"
