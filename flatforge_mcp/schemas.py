"""Pydantic input schemas for future structured tool validation."""
from pydantic import BaseModel, Field
class MeshInput(BaseModel):
    mesh: dict = Field(description="Mesh payload for the configured geometry engine")
class NestInput(BaseModel):
    parts: list[dict] = Field(description="Parts to arrange in a 2D sheet")
    sheet_width: float | None = None
    sheet_height: float | None = None
