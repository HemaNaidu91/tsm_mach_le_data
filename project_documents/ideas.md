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
### Snippets Model Registry(vibe written)
Step-by-Step Flow

Train your model

GNN → train on movie dataset → output model

1.Track and select your best model with W&B

Suppose you log your training to  W&B like this:
```python
import wandb
import torch

wandb.init(project="gnn-project")

# Training loop
for epoch in range(epochs):
    train_loss = train(model, data)
    val_acc = evaluate(model, val_data)
    wandb.log({"epoch": epoch, "train_loss": train_loss, "val_acc": val_acc})  # Here you track every run, compare metrics, visualize hyperparameter impact.

    # Save best model locally & to W&B
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), "best_model.pth")
        wandb.save("best_model.pth")
```
torch.save is safe for PyG models.
W&B keeps a record of every run → you can pick the best checkpoint.

2. Prepare for backend deployment (no ONNX)

Instead of ONNX, use TorchScript:
```python
import torch
from torch_geometric.data import Data

# Load your trained model
model.load_state_dict(torch.load("best_model.pth"))
model.eval()

# Example dummy input (graph with 5 nodes and 4 edges)
dummy_data = Data(x=torch.randn(5, num_features),
                  edge_index=torch.tensor([[0,1,2,3],[1,2,3,4]], dtype=torch.long))

# Trace the model
scripted_model = torch.jit.trace(model, (dummy_data.x, dummy_data.edge_index))
scripted_model.save("best_model_scripted.pt")
```
Advantages:

Fully backend-compatible (Python, C++, TorchScript runtime).
No ONNX conversion errors.
You can deploy in FastAPI or any server.

3. Load in backend for inference
```python
import torch
from torch_geometric.data import Data

# Load TorchScript model
model = torch.jit.load("best_model_scripted.pt")
model.eval()

# Example inference
data = Data(x=torch.randn(5, num_features),
            edge_index=torch.tensor([[0,1,2,3],[1,2,3,4]], dtype=torch.long))
with torch.no_grad():
    out = model(data.x, data.edge_index)
print(out)
```
Lightweight, fast, and safe.
Works for any PyG layer, even GAT or custom convolutions.


Architecture Diagram :

[Training]
   ->
[GNN Model] 
   ->
[W&B] (Experiment tracking: metrics, loss, hyperparams)
   ->
Save the scripted model using Torchscript
   ->
[FastAPI] (loads model)
   <->
[Streamlit] (UI for users)
 


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
