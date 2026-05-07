from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import onnxruntime as ort
import torch
import wandb
from torch_geometric.data import HeteroData
from dotenv import load_dotenv

from schemas import RatedMovie

load_dotenv()

LOGGER = logging.getLogger(__name__)

DEFAULT_ARTIFACT_ALIAS = "latest"
DEFAULT_ARTIFACT_NAME = "movie-rec-link-regression-weights"
DEFAULT_GRAPH_BUNDLE_NAME = "graph_bundle.pt"
DEFAULT_ONNX_MODEL_NAME = "graph_link_regression.onnx"
DEFAULT_TOP_K = 10


class PredictionValidationError(ValueError):
    pass


@dataclass(slots=True)
class LoadedGraphBundle:
    base_data: HeteroData
    movie_mapping: pd.DataFrame
    candidate_movies: pd.DataFrame


class RecommendationService:
    def __init__(
        self,
        *,
        session: ort.InferenceSession,
        device: str,
        available_providers: Sequence[str],
        onnx_path: Path,
        graph_bundle: LoadedGraphBundle,
        artifact_path: str,
        top_k: int,
    ) -> None:
        self.session = session
        self.device = device
        self.available_providers = tuple(available_providers)
        self.session_providers = tuple(session.get_providers())
        self.onnx_path = onnx_path
        self.onnx_output_name = session.get_outputs()[0].name
        self.base_data = graph_bundle.base_data
        self.movie_mapping = graph_bundle.movie_mapping
        self.candidate_movies = graph_bundle.candidate_movies
        self.movie_id_to_mapped = dict(
            zip(
                self.movie_mapping["movieId"].astype(int),
                self.movie_mapping["mappedMovieId"].astype(int),
                strict=False,
            )
        )
        self.artifact_path = artifact_path
        self.top_k = top_k

    @classmethod
    def load_from_env(cls) -> "RecommendationService":
        artifact_root = Path(
            os.getenv(
                "MODEL_SERVICE_ARTIFACT_CACHE_DIR",
                Path(__file__).resolve().parent / "artifacts",
            )
        )
        artifact_root.mkdir(parents=True, exist_ok=True)

        device, execution_providers = cls._resolve_runtime()
        artifact_dir, artifact_path = cls._resolve_artifact_dir(
            artifact_root=artifact_root,
        )

        onnx_path = artifact_dir / os.getenv(
            "MODEL_SERVICE_ONNX_FILE", DEFAULT_ONNX_MODEL_NAME
        )
        if not onnx_path.exists():
            raise RuntimeError(
                "ONNX model was not found in the artifact at "
                f"{onnx_path}. The model artifact must contain both "
                f"{DEFAULT_GRAPH_BUNDLE_NAME} and {onnx_path.name}."
            )

        graph_bundle_path = artifact_dir / os.getenv(
            "MODEL_SERVICE_GRAPH_BUNDLE_FILE", DEFAULT_GRAPH_BUNDLE_NAME
        )
        if not graph_bundle_path.exists():
            raise RuntimeError(
                "Graph bundle was not found in the artifact at "
                f"{graph_bundle_path}. The model artifact must contain both "
                f"{onnx_path.name} and {graph_bundle_path.name}."
            )

        graph_bundle = cls._load_graph_bundle(graph_bundle_path)
        LOGGER.info("Loaded graph bundle from %s.", graph_bundle_path)

        available_providers = ort.get_available_providers()
        session_options = ort.SessionOptions()
        session_options.log_severity_level = 3
        session = ort.InferenceSession(
            onnx_path.as_posix(),
            sess_options=session_options,
            providers=execution_providers,
        )
        active_device = cls._device_from_session(session)

        LOGGER.info(
            "Loaded recommendation ONNX model from %s using providers %s.",
            onnx_path,
            session.get_providers(),
        )
        return cls(
            session=session,
            device=active_device,
            available_providers=available_providers,
            onnx_path=onnx_path,
            graph_bundle=graph_bundle,
            artifact_path=artifact_path,
            top_k=int(os.getenv("MODEL_SERVICE_TOP_K", DEFAULT_TOP_K)),
        )

    @staticmethod
    def _load_graph_bundle(graph_bundle_path: Path) -> LoadedGraphBundle:
        bundle = torch.load(
            graph_bundle_path,
            map_location="cpu",
            weights_only=False,
        )
        if isinstance(bundle, LoadedGraphBundle):
            return LoadedGraphBundle(
                base_data=bundle.base_data.cpu(),
                movie_mapping=bundle.movie_mapping.copy(),
                candidate_movies=bundle.candidate_movies.copy(),
            )

        if not isinstance(bundle, dict):
            raise RuntimeError(
                f"Unexpected graph bundle format in {graph_bundle_path}."
            )

        base_data = bundle.get("base_data")
        movie_mapping = bundle.get("movie_mapping")
        candidate_movies = bundle.get("candidate_movies")

        if candidate_movies is None and isinstance(movie_mapping, pd.DataFrame):
            candidate_movies = movie_mapping[["movieId", "mappedMovieId"]].copy()

        if not isinstance(base_data, HeteroData):
            raise RuntimeError(
                f"Graph bundle {graph_bundle_path} is missing a valid base_data entry."
            )
        if not isinstance(movie_mapping, pd.DataFrame):
            raise RuntimeError(
                f"Graph bundle {graph_bundle_path} is missing a valid movie_mapping entry."
            )
        if not isinstance(candidate_movies, pd.DataFrame):
            raise RuntimeError(
                f"Graph bundle {graph_bundle_path} is missing a valid candidate_movies entry."
            )

        return LoadedGraphBundle(
            base_data=base_data.cpu(),
            movie_mapping=movie_mapping.copy(),
            candidate_movies=candidate_movies.copy(),
        )

    def predict(self, ratings: Sequence[RatedMovie]) -> list[dict[str, float | int]]:
        if not ratings:
            raise PredictionValidationError("At least one movie rating is required.")

        ratings_df = pd.DataFrame(
            [{"movieId": item.movie_id, "rating": item.rating} for item in ratings]
        )

        duplicate_ids = sorted(
            ratings_df.loc[ratings_df["movieId"].duplicated(), "movieId"].unique()
        )
        if duplicate_ids:
            raise PredictionValidationError(
                f"Duplicate movie ids are not allowed: {duplicate_ids}."
            )

        unknown_movie_ids = sorted(
            movie_id
            for movie_id in ratings_df["movieId"].astype(int).tolist()
            if movie_id not in self.movie_id_to_mapped
        )
        if unknown_movie_ids:
            raise PredictionValidationError(
                "Movie ids are not available in the trained graph: "
                f"{unknown_movie_ids}."
            )

        personal_ratings_df = ratings_df.merge(
            self.movie_mapping[["movieId", "mappedMovieId"]],
            on="movieId",
            how="inner",
        )

        infer_data = self.base_data.clone()
        new_user_id = infer_data["user"].x.size(0)
        feat_dim = infer_data["user"].x.size(1)
        new_user_x = torch.ones((1, feat_dim), dtype=infer_data["user"].x.dtype)
        infer_data["user"].x = torch.cat([infer_data["user"].x, new_user_x], dim=0)

        mapped_movie_ids = personal_ratings_df["mappedMovieId"].astype(int).tolist()
        rating_tensor = torch.tensor(
            personal_ratings_df["rating"].tolist(),
            dtype=infer_data["user", "rates", "movie"].edge_attr.dtype,
        ).unsqueeze(1)

        user_to_movie_edges = torch.stack(
            [
                torch.full((len(mapped_movie_ids),), new_user_id, dtype=torch.long),
                torch.tensor(mapped_movie_ids, dtype=torch.long),
            ],
            dim=0,
        )
        movie_to_user_edges = torch.stack(
            [
                torch.tensor(mapped_movie_ids, dtype=torch.long),
                torch.full((len(mapped_movie_ids),), new_user_id, dtype=torch.long),
            ],
            dim=0,
        )

        infer_data["user", "rates", "movie"].edge_index = torch.cat(
            [infer_data["user", "rates", "movie"].edge_index, user_to_movie_edges],
            dim=1,
        )
        infer_data["user", "rates", "movie"].edge_attr = torch.cat(
            [infer_data["user", "rates", "movie"].edge_attr, rating_tensor],
            dim=0,
        )

        infer_data["movie", "rev_rates", "user"].edge_index = torch.cat(
            [infer_data["movie", "rev_rates", "user"].edge_index, movie_to_user_edges],
            dim=1,
        )
        infer_data["movie", "rev_rates", "user"].edge_attr = torch.cat(
            [infer_data["movie", "rev_rates", "user"].edge_attr, rating_tensor],
            dim=0,
        )

        candidate_movies = self.candidate_movies.loc[
            ~self.candidate_movies["movieId"].isin(ratings_df["movieId"])
        ].copy()
        if candidate_movies.empty:
            raise PredictionValidationError("No candidate movies remain to score.")

        candidate_movie_ids = torch.tensor(
            candidate_movies["mappedMovieId"].values,
            dtype=torch.long,
        )
        candidate_user_ids = torch.full(
            (candidate_movie_ids.size(0),),
            new_user_id,
            dtype=torch.long,
        )
        edge_label_index = torch.stack([candidate_user_ids, candidate_movie_ids], dim=0)

        ort_inputs = {
            "user_x": infer_data["user"].x.detach().cpu().float().numpy(),
            "movie_x": infer_data["movie"].x.detach().cpu().float().numpy(),
            "rates_edge_index": infer_data["user", "rates", "movie"]
            .edge_index.detach()
            .cpu()
            .long()
            .numpy(),
            "rates_edge_attr": infer_data["user", "rates", "movie"]
            .edge_attr.detach()
            .cpu()
            .float()
            .numpy(),
            "rev_rates_edge_index": infer_data["movie", "rev_rates", "user"]
            .edge_index.detach()
            .cpu()
            .long()
            .numpy(),
            "rev_rates_edge_attr": infer_data["movie", "rev_rates", "user"]
            .edge_attr.detach()
            .cpu()
            .float()
            .numpy(),
            "edge_label_index": edge_label_index.detach().cpu().long().numpy(),
        }
        pred = self.session.run([self.onnx_output_name], ort_inputs)[0]
        pred = np.clip(np.asarray(pred).reshape(-1), 0.0, 5.0)

        recommendations_df = candidate_movies[["movieId"]].copy()
        recommendations_df["predicted_rating"] = pred
        recommendations_df = recommendations_df.sort_values(
            ["predicted_rating", "movieId"],
            ascending=[False, True],
        ).head(self.top_k)

        return [
            {
                "movie_id": int(movie_id),
                "predicted_rating": float(predicted_rating),
            }
            for movie_id, predicted_rating in recommendations_df.itertuples(index=False)
        ]

    @staticmethod
    def _resolve_runtime() -> tuple[str, list[str]]:
        requested_device = os.getenv("MODEL_SERVICE_DEVICE", "auto").lower()
        available_providers = ort.get_available_providers()

        if requested_device == "auto":
            if "CUDAExecutionProvider" in available_providers:
                return "cuda", ["CUDAExecutionProvider", "CPUExecutionProvider"]
            return "cpu", ["CPUExecutionProvider"]

        if requested_device.startswith("cuda"):
            if "CUDAExecutionProvider" not in available_providers:
                raise RuntimeError(
                    "CUDA was requested but ONNX Runtime CUDAExecutionProvider is not available."
                )
            return requested_device, ["CUDAExecutionProvider", "CPUExecutionProvider"]

        if requested_device != "cpu":
            raise RuntimeError(
                "MODEL_SERVICE_DEVICE must be one of auto, cpu, or cuda."
            )
        return "cpu", ["CPUExecutionProvider"]

    @staticmethod
    def _device_from_session(session: ort.InferenceSession) -> str:
        session_providers = session.get_providers()
        if "CUDAExecutionProvider" in session_providers:
            return "cuda"
        return "cpu"

    @classmethod
    def _resolve_artifact_dir(cls, *, artifact_root: Path) -> tuple[Path, str]:
        wandb_entity = os.getenv("WANDB_ENTITY")
        wandb_project = os.getenv("WANDB_PROJECT")
        artifact_name = os.getenv("WANDB_ARTIFACT_NAME", DEFAULT_ARTIFACT_NAME)
        artifact_alias = os.getenv("WANDB_ARTIFACT_ALIAS", DEFAULT_ARTIFACT_ALIAS)
        if not wandb_entity or not wandb_project:
            raise RuntimeError(
                "WANDB_ENTITY and WANDB_PROJECT must be set before loading artifacts."
            )

        artifact_path = (
            f"{wandb_entity}/{wandb_project}/{artifact_name}:{artifact_alias}"
        )
        try:
            wandb.login(key=os.getenv("WANDB_API_KEY")) # added to fetch from online
            api = wandb.Api()
            artifact = api.artifact(artifact_path, type="model")
            download_dir = artifact_root / f"{artifact_name}_{artifact.version}"
            artifact_dir = Path(artifact.download(root=download_dir.as_posix()))
            return artifact_dir, artifact_path
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised in runtime fallback only
            LOGGER.warning(
                "Falling back to a local cached artifact because W&B download failed: %s",
                exc,
            )
            local_artifact_dir = cls._find_local_artifact_dir(
                artifact_root=artifact_root,
                artifact_name=artifact_name,
            )
            if local_artifact_dir is None:
                raise RuntimeError(
                    "Unable to download the latest W&B artifact and no local cache was found inside "
                    f"{artifact_root}."
                ) from exc
            return local_artifact_dir, artifact_path

    @staticmethod
    def _find_local_artifact_dir(
        *, artifact_root: Path, artifact_name: str
    ) -> Path | None:
        graph_bundle_filename = os.getenv(
            "MODEL_SERVICE_GRAPH_BUNDLE_FILE", DEFAULT_GRAPH_BUNDLE_NAME
        )
        onnx_filename = os.getenv("MODEL_SERVICE_ONNX_FILE", DEFAULT_ONNX_MODEL_NAME)
        bundle_candidates: list[Path] = []
        if not artifact_root.exists():
            return None

        for path in artifact_root.glob(f"{artifact_name}*"):
            if not path.is_dir():
                continue
            if (path / graph_bundle_filename).exists() and (
                path / onnx_filename
            ).exists():
                bundle_candidates.append(path)

        if bundle_candidates:
            return max(
                bundle_candidates, key=lambda candidate: candidate.stat().st_mtime
            )
        return None
