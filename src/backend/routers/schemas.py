from pydantic import BaseModel


class VersionResponse(BaseModel):
    version: float
