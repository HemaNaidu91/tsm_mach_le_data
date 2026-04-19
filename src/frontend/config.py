"""Define configuration values for the Streamlit frontend.

This module loads optional environment variables from a local ``.env`` file and
defines the constants used across the CineMatch frontend. Centralizing these
values keeps rating limits, API configuration, recommendation settings, and
default profile values consistent across the application.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

TOP_K_RECOMMENDATIONS = 3
MIN_RATING = 0.5
MAX_RATING = 5.0
RATING_STEP = 0.5
MAX_SEARCH_RESULTS = 10

DEFAULT_RATING = 2.5
DEFAULT_PROFILE_ID = "user_1"
DEFAULT_PROFILE_NAME = "User 1"
