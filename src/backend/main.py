from fastapi import FastAPI
from routers import recommendation_router
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import os


# load env variables
load_dotenv()
# TBD: str = os.getenv("TBD")


# setup app
app = FastAPI()
app.include_router(
    recommendation_router.router, prefix="/recommendations", tags=["recommendations"]
)

# setup cors
origins: list = [
    "http://localhost:8501",  # default port for streamlit
    "https://localhost:8501",  # default port for streamlit
    # "*", #use this if all else fails
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
