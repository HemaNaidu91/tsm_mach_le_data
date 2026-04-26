# Movie Recommendation Model Service

This FastAPI service downloads the latest W&B link regression artifact, loads the saved checkpoint plus the prebuilt graph bundle, and returns the top 10 unseen movies for a rated input set.

## Required environment variables

- `WANDB_API_KEY`
- `WANDB_ENTITY`
- `WANDB_PROJECT`

## Optional environment variables

- `WANDB_ARTIFACT_NAME` defaults to `movie-rec-link-regression-weights`
- `WANDB_ARTIFACT_ALIAS` defaults to `latest`
- `MODEL_SERVICE_GRAPH_BUNDLE_FILE` defaults to `graph_bundle.pt`
- `MODEL_SERVICE_DEVICE` defaults to `auto`
- `MODEL_SERVICE_TOP_K` defaults to `10`
- `MODEL_SERVICE_ARTIFACT_CACHE_DIR` defaults to `./artifacts`
- `PORT` defaults to `8001`

## Run locally

Create a virtual environment:

```
uv venv .venv --python=3.12.4
```

If you have a GPU and cuda installed, use:

```
uv pip install -r pyproject.toml --extra gpu
```

Otherwise, use:

```
uv pip install -r pyproject.toml --extra cpu
```

Then, start the service:

```
.\.venv\Scripts\python.exe model-service.py
```

The first startup downloads the latest W&B artifact into the local `artifacts` folder. If W&B is unavailable, the service only falls back to cached artifacts inside that same folder.

## Example request

If you use powershell, you can test the service with:

```powershell
$body = @'
[
  { "movieId": 356, "rating": 5.0 },
  { "movieId": 318, "rating": 4.0 },
  { "movieId": 296, "rating": 5.0 },
  { "movieId": 593, "rating": 3.0 },
  { "movieId": 2571, "rating": 5.0 },
  { "movieId": 260, "rating": 3.0 },
  { "movieId": 480, "rating": 3.0 },
  { "movieId": 110, "rating": 1.0 },
  { "movieId": 589, "rating": 4.0 },
  { "movieId": 527, "rating": 3.0 }
]
'@
```

```powershell
Invoke-RestMethod `
   -Uri "http://localhost:8001/predict" `
   -Method Post `
   -ContentType "application/json" `
   -Body $body
```

## Example response

```json
[
  { "movieId": 858, "predictedRating": 4.92 },
  { "movieId": 1221, "predictedRating": 4.88 }
]
```
