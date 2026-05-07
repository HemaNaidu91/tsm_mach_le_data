import os
from importlib import import_module
from main import app
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    uvicorn = import_module("uvicorn")
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8001)),
    )
