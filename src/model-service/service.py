from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd
import torch
import wandb
from torch_geometric.data import HeteroData

from graph_regression import Model
from schemas import RatedMovie


LOGGER = logging.getLogger(__name__)

DEFAULT_ARTIFACT_ALIAS = "latest"
DEFAULT_ARTIFACT_NAME = "movie-rec-link-regression-weights"
DEFAULT_GRAPH_BUNDLE_NAME = "graph_bundle.pt"
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
        model: Model,
        device: torch.device,
        graph_bundle: LoadedGraphBundle,
        artifact_path: str,
        artifact_dir: Path,
        checkpoint_epoch: int | None,
        checkpoint_val_rmse: float | None,
        top_k: int,
    ) -> None:
        self.model = model
        self.device = device
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
        self.artifact_dir = artifact_dir
        self.checkpoint_epoch = checkpoint_epoch
        self.checkpoint_val_rmse = checkpoint_val_rmse
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

        device = cls._resolve_device()
        artifact_dir, artifact_path = cls._resolve_artifact_dir(
            artifact_root=artifact_root,
        )
        checkpoint_path = artifact_dir / "model_best.pt"
        if not checkpoint_path.exists():
            raise RuntimeError(f"Checkpoint not found at {checkpoint_path}.")

        checkpoint = torch.load(
            checkpoint_path,
            map_location=device,
            weights_only=False,
        )

        graph_bundle_path = artifact_dir / os.getenv(
            "MODEL_SERVICE_GRAPH_BUNDLE_FILE", DEFAULT_GRAPH_BUNDLE_NAME
        )
        if not graph_bundle_path.exists():
            raise RuntimeError(
                "Graph bundle was not found in the artifact at "
                f"{graph_bundle_path}. The model artifact must contain both "
                f"model_best.pt and {graph_bundle_path.name}."
            )

        graph_bundle = cls._load_graph_bundle(graph_bundle_path)
        LOGGER.info("Loaded graph bundle from %s.", graph_bundle_path)

        hidden_channels = checkpoint["config"]["hidden_channels"]
        model = Model(
            hidden_channels=hidden_channels,
            metadata=graph_bundle.base_data.metadata(),
        ).to(device)

        warmup_data = graph_bundle.base_data.clone().to(device)
        with torch.no_grad():
            model(
                warmup_data.x_dict,
                warmup_data.edge_index_dict,
                warmup_data.edge_attr_dict,
                warmup_data["user", "rates", "movie"].edge_index,
            )

        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()

        LOGGER.info("Loaded recommendation model from %s on %s.", artifact_path, device)
        return cls(
            model=model,
            device=device,
            graph_bundle=graph_bundle,
            artifact_path=artifact_path,
            artifact_dir=artifact_dir,
            checkpoint_epoch=checkpoint.get("epoch"),
            checkpoint_val_rmse=checkpoint.get("val_rmse"),
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

        infer_data = infer_data.to(self.device)
        candidate_movie_ids = torch.tensor(
            candidate_movies["mappedMovieId"].values,
            dtype=torch.long,
            device=self.device,
        )
        candidate_user_ids = torch.full(
            (candidate_movie_ids.size(0),),
            new_user_id,
            dtype=torch.long,
            device=self.device,
        )
        edge_label_index = torch.stack([candidate_user_ids, candidate_movie_ids], dim=0)

        self.model.eval()
        with torch.inference_mode():
            pred = self.model(
                infer_data.x_dict,
                infer_data.edge_index_dict,
                infer_data.edge_attr_dict,
                edge_label_index,
            )
            pred = pred.clamp(min=0, max=5).detach().cpu().numpy()

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
    def _resolve_device() -> torch.device:
        requested_device = os.getenv("MODEL_SERVICE_DEVICE", "auto").lower()
        if requested_device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if requested_device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available.")
        return torch.device(requested_device)

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
        bundle_candidates: list[Path] = []
        checkpoint_only_candidates: list[Path] = []
        if not artifact_root.exists():
            return None

        for path in artifact_root.glob(f"{artifact_name}*"):
            if path.is_dir() and (path / "model_best.pt").exists():
                if (path / graph_bundle_filename).exists():
                    bundle_candidates.append(path)
                else:
                    checkpoint_only_candidates.append(path)

        if bundle_candidates:
            return max(
                bundle_candidates, key=lambda candidate: candidate.stat().st_mtime
            )
        if checkpoint_only_candidates:
            return max(
                checkpoint_only_candidates,
                key=lambda candidate: candidate.stat().st_mtime,
            )
        return None
