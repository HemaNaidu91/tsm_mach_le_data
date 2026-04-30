# Movie Recommendation Model Service

This FastAPI service downloads the latest W&B link regression artifact, loads the exported ONNX model plus the prebuilt graph bundle, and returns the top 10 unseen movies for a rated input set.

## Required environment variables

- `WANDB_API_KEY`
- `WANDB_ENTITY`
- `WANDB_PROJECT`

## Optional environment variables

- `WANDB_ARTIFACT_NAME` defaults to `movie-rec-link-regression-weights`
- `WANDB_ARTIFACT_ALIAS` defaults to `latest`
- `MODEL_SERVICE_GRAPH_BUNDLE_FILE` defaults to `graph_bundle.pt`
- `MODEL_SERVICE_ONNX_FILE` defaults to `graph_link_regression.onnx`
- `MODEL_SERVICE_DEVICE` defaults to `auto`
- `MODEL_SERVICE_TOP_K` defaults to `10`
- `MODEL_SERVICE_ARTIFACT_CACHE_DIR` defaults to `./artifacts`
- `PORT` defaults to `8001`

## Run locally

Create a virtual environment:

```
uv venv .venv --python=3.12.4
```

Activate it:

```
.\.venv\Scripts\activate
```

If you have a GPU and cuda installed, use:

```
uv pip install -r pyproject.toml --extra gpu
```

This installs `onnxruntime-gpu`, which is required for `CUDAExecutionProvider` to appear.

Otherwise, use:

```
uv pip install -r pyproject.toml --extra cpu
```

This installs the CPU-only `onnxruntime` package.

Then, start the service:

```
python model-service.py
```

The first startup downloads the latest W&B artifact into the local `artifacts` folder. The service only needs `graph_link_regression.onnx` and `graph_bundle.pt` from that artifact. If W&B is unavailable, it only falls back to cached artifacts inside that same folder.

The `/health` endpoint reports both `available_providers` and `session_providers`, so you can see whether ONNX Runtime actually has CUDA support and whether the running session is using it.

## Run with Docker

Build the default CPU image from the repository root:

```bash
docker build -t movie-rec-model-service:cpu src/model-service
```

Run the service with the environment variables from `.env`:

```bash
docker run --rm \
  --env-file src/model-service/.env \
  -p 8001:8001 \
  -v "$(pwd)/src/model-service/artifacts:/app/artifacts" \
  movie-rec-model-service:cpu
```

The volume mount keeps downloaded W&B artifacts on the host, so restarts can reuse the local `artifacts` cache.

To build the image with GPU dependencies instead, use:

```bash
docker build \
  --build-arg MODEL_SERVICE_EXTRA=gpu \
  -t movie-rec-model-service:gpu \
  src/model-service
```

Then run it with Docker's GPU runtime enabled:

```bash
docker run --rm \
  --gpus all \
  --env-file src/model-service/.env \
  -e MODEL_SERVICE_DEVICE=cuda \
  -p 8001:8001 \
  -v "$(pwd)/src/model-service/artifacts:/app/artifacts" \
  movie-rec-model-service:gpu
```

After startup, check the service:

```bash
curl http://localhost:8001/health
```

## Example request

If you use macOS/Linux, you can test the service with:

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '[
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
  ]'
```

If you use PowerShell, you can test the service with:

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
