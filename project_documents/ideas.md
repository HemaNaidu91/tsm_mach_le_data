# Project Outline Idea

## Goal and Parameters
- Create movie recommendations based on cosine similarity
- Data: The TMDB used as a base (see: https://www.themoviedb.org/)
- Input: List of user chosen movies (length tdb)
- Output: List of recommended or similar movies

## General
- Data stored in RDBMS
- Prediction model:
    - Create custom dense embeddings for the movie
    - Predictions: Create embeddings for each input movie, average them, calculate cosine similarity
- Prediction available over an API and over a GUI
- GUI uses the API endpoint

## Tooling
| Tool | Purpose |
|------|---------|
| GitHub | Version control and deployment pipeline |
| PostgreSQL | Database |
| PYG | GNN Library |
| Streamlit | Web GUI and processing user inputs |
| FastAPI | RESTful interface for requesting recommendations and using Streamlit connection |
| Docker | Containerization (one container for Streamlit and Backend and FastAPI) |
| ONNX | Save and use model |
| Some Hosting Provider | PVD |
| WANDB| Training and Hyperparam optimisation |
| RUFF | Linting and Formatting (on saving) |
| OPT: Github Actions| Building (if we host the application somewhere) |
| OPT: Airflow | Task schedueling |
| OPT: DVC| Data Versioning for the Flywheel |

## Application "Architecture" (on VPS or local)
- ML Workflow:
    - Data > Train model > save model with WANDB > package model with ONNX > deploy it to DVC model registry 
- DB Server on VPS or Supabase
- Container backend:
    - Pretrained ONNX Model file
    - ORM Connection to DB
    - FastAPI Interface
- Container frontend:
    - Streamlit app
    - Connecting to the FastAPI Service over web

## Questions:
- How do we get the versioned model into the container? during build time via dockerfile or pipeline?
## Snippets Model Registry
Step-by-Step Flow

Train your model

GNN → train on movie dataset → output model

Log experiments to W&B
```python
import wandb

wandb.init(project="movie-recommender")
wandb.log({"loss": loss, "accuracy": acc})
```
 Here you track every run, compare metrics, visualize hyperparameter impact.

Convert model to ONNX
```python
torch.onnx.export(model, dummy_input, "movie_model.onnx")
```
Log model to MLflow registry
```python
import mlflow.onnx

mlflow.start_run()
mlflow.onnx.log_model(onnx_model=model, artifact_path="model")
mlflow.end_run()
```
Register version in MLflow
```python
mlflow.register_model(
    "runs:/<run_id>/model",
    "movie-recommender-model"
)
```
Deploy model from MLflow in FastAPI
```python
import mlflow.onnx

model = mlflow.onnx.load_model("models:/movie-recommender-model/Production")
```
Architecture Diagram With Both:

[Training]
   ↓
[GNN Model] 
   ↓
[W&B] (Experiment tracking: metrics, loss, hyperparams)
   ↓
Convert → ONNX
   ↓
[MLflow] (Model registry: store, version, promote)
   ↓
[FastAPI] (loads model)
   ↓
[Streamlit] (UI for users)
 

Important:

W&B does not feed the model into FastAPI
MLflow is used only to serve the model to FastAPI

Benefits of Using Both:
W&B
Real-time dashboards
Compare different GNN hyperparameters
Team collaboration
MLflow
Model versioning
Clean separation between experimental & production models
Easy rollback & deployment
(vibe coded)

## Project structure (vibe written)
Note: The PostgreSQL instance has to be set up independently.

```
your-repo/
├── .github/
│   └── workflows/
│       ├── deploy.yml          # main pipeline
│       └── train.yml           # optional: retrain model
├── backend/
│   ├── Dockerfile
│   ├── main.py                 # FastAPI
│   ├── model/
│   │   └── movie_encoder.onnx
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   └── app.py                  # Streamlit
├── training/
│   └── train.py                # PyTorch training script
└── docker-compose.yml
```


Notes on interfaces:

Model M - Backend B:
- B --> M: [{"movie": some_id, "rating": some_rating}, {...}]
- M --> B: [{"movie": some_id, "sim_score": some_score}, {...}]

Backend B - Frontend F:
- B --> F: [ {"movie":some_id, "tags" : ...}, {} ]
- F --> B: [{"movie": some_id, "rating": some_rating}, {...}]

Ports: defaults from FastAPI, Streamlit, and Postgres
