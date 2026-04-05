# GNN-Based Movie Recommendation Model

This part of the repo contains the code for training a Graph Neural Network (GNN) based movie recommendation model using PyTorch Geometric. The model is designed to use the relationships between users and movies to provide personalized recommendations.

## Getting started

The setup describes the CPU or GPU based training of the GNN model.

### Installation (Windows)

Make sure [uv](https://docs.astral.sh/uv/getting-started/installation/) is installed on your system. Then, create and activate a virtual environment:

```bash
uv venv .venv --python=3.12.4
```

```bash
.venv\Scripts\activate
```

If you are using a GPU, make sure CUDA Toolkit is installed. Then run:

```bash
uv sync --extra gpu
```

Otherwise run:

```bash
uv sync --extra cpu
```

Registering the ipykernel for VS Code Jupyter Notebooks:

```bash
python -m ipykernel install --user --name=.venv --display-name "ML Ops (training)"
```

Add a `.env` file in the `training` folder with the following content:

```env
WANDB_API_KEY=your_actual_api_key
WANDB_PROJECT=movie-recsys-pyg
WANDB_ENTITY=your_username_or_team
```
