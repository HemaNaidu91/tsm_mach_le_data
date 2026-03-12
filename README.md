# MSE TSM MachLeData Group Project

## About the Project

Repo for the Groupproject TSM MachLeData.<br>
Project members:

- Hemanthi Naidu
- Pedro Stark
- ...
- Joël Tauss

Goal:

- Building a movie reccomendation system with sklearn and pytorch
- Creating a deployment pipeline
- Building and hosting the application

See project_documents for furher information

## Tooling and software requirements

| Software / Tool | Version | Link                                            |
| --------------- | ------- | ----------------------------------------------- |
| Python          | 3.12    | https://www.python.org/downloads/               |
| PostgresQL      | 18      | https://www.postgresql.org/download/            |
| Docker Desktop  | 4.19    | https://docs.docker.com/get-started/get-docker/ |
| ...             | ...     | ...                                             |

## Data

The following data can be to build a baseline model:

- [MovieLens: ml-latest.zip](https://files.grouplens.org/datasets/movielens/) - It contains 33'832'162 ratings and 2'328'315 tag applications across 86'537 movies. These data were created by 330'975 users between January 09, 1995 and July 20, 2023. This dataset was generated on July 20, 2023.

## Getting Started

### Setting up the python environment

1. Make sure uv is installed
   https://docs.astral.sh/uv/getting-started/installation/

2. Creating a virtual environment

```sh
uv venv .venv --python=3.12.4
```

3. Activating the virtual environment

On macOS/Linux:

```sh
source .venv/bin/activate
```

On Windows (PowerShell):

```sh
.venv\Scripts\Activate
```

4. Installing the dependencies

```sh
uv pip install -r requirements.txt
```
