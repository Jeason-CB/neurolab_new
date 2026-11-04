from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = ""
    family: str = "Feedforward"

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; description: str; family: str; status: str; owner: str

class ArchitectureCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    family: str
    config_json: dict[str, Any]

class DatasetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    format: str = "CSV"
    description: str = ""
    status: str = "Borrador"
    metadata_json: dict[str, Any] = {}

class TrainingCreate(BaseModel):
    architecture_id: int
    dataset_id: int
    epochs: int = Field(default=5, ge=1, le=200)
    batch_size: int = Field(default=32, ge=1, le=512)
    optimizer: str = "adam"

class CancelOut(BaseModel):
    message: str
