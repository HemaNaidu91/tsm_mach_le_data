from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import os

from routers.version import router as version_router
from routers.recommendation import router as recommendation_router
from routers.enum import router as enum_router


# load env variables
load_dotenv()
# TBD: str = os.getenv("TBD")

swagger_ui_parameters = {"syntaxHighlight": {"theme": os.getenv("SWAGGER_THEME")}}
description: str = """
Project for module: TSM_MachLeData (ML Ops)
This FastAPI serves as:
- Backend for the Streamlit GUI
- Standalone RestAPI service
"""

# setup app
app = FastAPI(
    title=os.getenv("TITLE"),
    description=description,
    summary="Cinematch API: Project for TSM_MachLeData",
    version=os.getenv("VERSION_NR"),
    swagger_ui_parameters=swagger_ui_parameters,
)

# add routers (this could be optimized but is sufficient for two routers)
app.include_router(version_router, prefix="/api", tags=["version"])
app.include_router(
    recommendation_router, prefix="/api/recommendation", tags=["recommendation"]
)
app.include_router(enum_router, prefix="/api/enum", tags=["enums"])


# setup cors
origins: list = [
    "http://localhost:8501",  # default port for streamlit
    "https://localhost:8501",  # default port for streamlit
    "http://127.0.0.1:8501",
    "https://127.0.0.1:8501",
    # "*", #use this if all else fails
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
