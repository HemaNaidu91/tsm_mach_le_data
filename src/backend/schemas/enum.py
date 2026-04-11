from pydantic import BaseModel
from typing import Optional, List


class GenresResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
