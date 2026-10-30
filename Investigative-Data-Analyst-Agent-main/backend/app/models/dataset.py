"""
SQLAlchemy 2.0 ORM model for the datasets table.
"""
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Dataset(Base):
    """
    Represents an uploaded dataset file with metadata such as shape,
    schema info, and storage details.
    """
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int] = mapped_column(Integer, nullable=True)
    schema_info: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string {col: dtype}
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    # FK reserved for future investigation linkage
    investigation_id: Mapped[int] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Dataset id={self.id} filename={self.filename!r} "
            f"type={self.file_type!r}>"
        )
