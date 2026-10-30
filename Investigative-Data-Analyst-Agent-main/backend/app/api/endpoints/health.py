from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from loguru import logger

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Verify the application status and SQLite database connectivity.
    Returns HTTP 200 with JSON detailing the health status of components.
    """
    logger.debug("Health check requested")
    try:
        # Run a simple query to assert DB is alive
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: database connectivity issue. Error: {e}")
        return {
            "status": "unhealthy",
            "database": f"error: {str(e)}"
        }
