"""
UploadService: handles file persistence, schema detection, and metadata extraction.
"""
import io
import json
import os
import uuid
from pathlib import Path

import pandas as pd
from loguru import logger

# Directory where uploaded datasets are stored
UPLOAD_DIR = Path(r"c:\Users\Home\OneDrive\Desktop\IDAA\backend\uploads")

# Supported file types mapped to their pandas reader
SUPPORTED_TYPES: dict[str, str] = {
    ".csv": "csv",
    ".xlsx": "xlsx",
}


class UploadService:
    """
    Handles saving uploaded files to disk, detecting their schema,
    and computing row/column counts.
    """

    def __init__(self) -> None:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_content: bytes, original_filename: str) -> dict:
        """
        Persist an uploaded file, inspect its contents, and return metadata.

        Args:
            file_content: Raw bytes of the uploaded file.
            original_filename: Original name provided by the client.

        Returns:
            dict containing: filename, stored_filename, file_path, file_type,
            row_count, column_count, schema_info (dict), file_size_bytes.

        Raises:
            ValueError: If the file extension is not supported.
        """
        suffix = Path(original_filename).suffix.lower()
        if suffix not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                f"Supported types: {list(SUPPORTED_TYPES.keys())}"
            )

        # Generate a UUID-based stored filename to avoid collisions
        stored_filename = f"{uuid.uuid4().hex}{suffix}"
        file_path = UPLOAD_DIR / stored_filename

        # Write file to disk
        file_path.write_bytes(file_content)
        file_size_bytes = file_path.stat().st_size
        logger.info(
            f"Saved uploaded file '{original_filename}' as '{stored_filename}' "
            f"({file_size_bytes} bytes)"
        )

        # Inspect content with pandas
        df = self.read_dataset(str(file_path))
        schema_info = {col: str(dtype) for col, dtype in df.dtypes.items()}

        return {
            "filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": str(file_path),
            "file_type": suffix.lstrip("."),
            "row_count": len(df),
            "column_count": len(df.columns),
            "schema_info": json.dumps(schema_info),
            "file_size_bytes": file_size_bytes,
        }

    def read_dataset(self, file_path: str) -> pd.DataFrame:
        """
        Load a CSV or XLSX file into a pandas DataFrame.

        Args:
            file_path: Absolute path to the file on disk.

        Returns:
            Parsed pandas DataFrame.

        Raises:
            ValueError: If the extension is not supported.
        """
        suffix = Path(file_path).suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(file_path)
        elif suffix == ".xlsx":
            return pd.read_excel(file_path, engine="openpyxl")
        else:
            raise ValueError(f"Cannot read unsupported file type: '{suffix}'")

    def delete_file(self, file_path: str) -> bool:
        """
        Remove a file from disk.

        Args:
            file_path: Absolute path to the file.

        Returns:
            True if deleted, False if file not found.
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        logger.warning(f"File not found for deletion: {file_path}")
        return False
