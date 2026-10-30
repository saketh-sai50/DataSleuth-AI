"""
Repository for Dataset database operations using SQLAlchemy 2.0 style.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.dataset import Dataset
from loguru import logger


class DatasetRepository:
    """
    Provides CRUD operations for Dataset model using clean repository pattern.
    Injected with a SQLAlchemy Session from FastAPI Depends().
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, dataset_data: dict) -> Dataset:
        """Create and persist a new Dataset record."""
        dataset = Dataset(**dataset_data)
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        logger.info(f"Dataset created: id={dataset.id}, filename={dataset.filename!r}")
        return dataset

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        """Retrieve a single Dataset by its primary key."""
        stmt = select(Dataset).where(Dataset.id == dataset_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_all(self) -> list[Dataset]:
        """Retrieve all Dataset records ordered by upload_timestamp descending."""
        stmt = select(Dataset).order_by(Dataset.upload_timestamp.desc())
        results = self.db.execute(stmt).scalars().all()
        return list(results)

    def delete(self, dataset_id: int) -> bool:
        """Delete a Dataset record by id. Returns True if deleted, False if not found."""
        dataset = self.get_by_id(dataset_id)
        if dataset is None:
            logger.warning(f"Attempted to delete non-existent Dataset id={dataset_id}")
            return False
        self.db.delete(dataset)
        self.db.commit()
        logger.info(f"Dataset deleted: id={dataset_id}")
        return True
