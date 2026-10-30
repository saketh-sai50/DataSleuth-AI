from fastapi import APIRouter
from app.api.endpoints import health, datasets, investigations, reports

api_router = APIRouter()

# Register endpoint groups
api_router.include_router(health.router, tags=["health"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

