"""
Pydantic v2 schemas for Dataset upload, response, and listing.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class DatasetCreate(BaseModel):
    """Schema for creating a new dataset record."""
    filename: str
    file_type: str


class DatasetResponse(BaseModel):
    """Schema returned by the API after a dataset is uploaded or queried."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    stored_filename: str
    file_type: str
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    schema_info: Optional[dict[str, Any]] = None
    file_size_bytes: Optional[int] = None
    upload_timestamp: datetime


class DatasetListResponse(BaseModel):
    """Schema for listing multiple datasets."""
    model_config = ConfigDict(from_attributes=True)

    datasets: list[DatasetResponse]
    total: int
