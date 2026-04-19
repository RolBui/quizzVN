from typing import Literal

from pydantic import BaseModel


class RootResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DbCheckResponse(BaseModel):
    database: Literal["connected", "failed"]


class MessageResponse(BaseModel):
    message: str
