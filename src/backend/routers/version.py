from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.version import VersionResponse

# load env variables
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()


@router.get("/version", response_model=VersionResponse)
async def get_version():
    return VersionResponse(version=float(os.getenv("VERSION_NR")))
