from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware


from schemas import RatedMovie, RecommendedMovie
from service import PredictionValidationError, RecommendationService


load_dotenv()


def _cors_origins() -> list[str]:
    configured_origins = os.getenv("MODEL_SERVICE_CORS_ORIGINS")
    if configured_origins:
        return [
            origin.strip() for origin in configured_origins.split(",") if origin.strip()
        ]
    return [
        "http://localhost:8501",
        "https://localhost:8501",
        "http://127.0.0.1:8501",
        "https://127.0.0.1:8501",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.recommendation_service = RecommendationService.load_from_env()
    yield


app = FastAPI(
    title=os.getenv("TITLE", "Movie Recommendation Model Service"),
    summary="FastAPI service for graph-based movie recommendations.",
    description=(
        "Loads the latest W&B link regression checkpoint and scores unseen MovieLens "
        "movies from a list of rated movie ids."
    ),
    version=os.getenv("VERSION_NR", "0.1.0"),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_recommendation_service(request: Request) -> RecommendationService:
    return request.app.state.recommendation_service


@app.get("/health")
def health(
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    return {
        "status": "ok",
        "artifact_path": recommendation_service.artifact_path,
        "device": str(recommendation_service.device),
        "checkpoint_epoch": recommendation_service.checkpoint_epoch,
        "checkpoint_val_rmse": recommendation_service.checkpoint_val_rmse,
    }


@app.post(
    "/predict", response_model=list[RecommendedMovie], response_model_by_alias=True
)
def predict(
    payload: list[RatedMovie],
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    try:
        recommendations = recommendation_service.predict(payload)
    except PredictionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [RecommendedMovie(**recommendation) for recommendation in recommendations]
