from pydantic import BaseModel
from typing import Optional, List


class VersionResponse(BaseModel):
    version: float

    class Config:
        from_attributes = True
