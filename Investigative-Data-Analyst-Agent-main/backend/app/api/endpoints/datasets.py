"""
FastAPI router for dataset upload, listing, retrieval, and deletion endpoints.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.dataset_repository import DatasetRepository
from app.schemas.dataset import DatasetResponse, DatasetListResponse
from app.services.upload_service import UploadService
from loguru import logger

router = APIRouter()


def _to_response(dataset) -> DatasetResponse:
    """Convert a Dataset ORM object to a DatasetResponse schema."""
    schema_info: Optional[dict] = None
    if dataset.schema_info:
        try:
            schema_info = json.loads(dataset.schema_info)
        except (json.JSONDecodeError, TypeError):
            schema_info = {}

    return DatasetResponse(
        id=dataset.id,
        filename=dataset.filename,
        stored_filename=dataset.stored_filename,
        file_type=dataset.file_type,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        schema_info=schema_info,
        file_size_bytes=dataset.file_size_bytes,
        upload_timestamp=dataset.upload_timestamp,
    )


@router.post(
    "/upload",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV or XLSX dataset",
)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """
    Accept a multipart file upload, save it to disk, extract schema metadata,
    and persist the record to the database.
    """
    logger.info(f"Upload request received for file: {file.filename!r}")
    upload_service = UploadService()
    repo = DatasetRepository(db)

    file_content = await file.read()

    try:
        metadata = upload_service.save_file(file_content, file.filename or "unknown")
    except ValueError as exc:
        logger.warning(f"Upload rejected: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    dataset = repo.create(metadata)
    return _to_response(dataset)


@router.get(
    "/",
    response_model=DatasetListResponse,
    summary="List all uploaded datasets",
)
def list_datasets(db: Session = Depends(get_db)) -> DatasetListResponse:
    """Return all datasets currently stored in the database."""
    repo = DatasetRepository(db)
    datasets = repo.get_all()
    return DatasetListResponse(
        datasets=[_to_response(d) for d in datasets],
        total=len(datasets),
    )


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Retrieve a single dataset by ID",
)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> DatasetResponse:
    """Retrieve metadata for a single dataset by its primary key."""
    repo = DatasetRepository(db)
    dataset = repo.get_by_id(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id={dataset_id} not found.",
        )
    return _to_response(dataset)


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dataset record and its file",
)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)) -> None:
    """Delete the dataset record from DB and remove the file from disk."""
    repo = DatasetRepository(db)
    dataset = repo.get_by_id(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with id={dataset_id} not found.",
        )

    file_path = dataset.file_path
    deleted = repo.delete(dataset_id)

    if deleted and file_path:
        upload_service = UploadService()
        upload_service.delete_file(file_path)

    logger.info(f"Dataset id={dataset_id} and associated file deleted.")
