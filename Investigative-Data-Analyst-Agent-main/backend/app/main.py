from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.session import Base, engine
from app.db import base  # noqa: F401 — registers all ORM models with Base.metadata
from app.api.router import api_router
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Sets up structured logging and ensures SQLite tables are created.
    """
    # 1. Setup logging configuration
    setup_logging()
    
    # 2. Database table generation (for MVP local DB)
    logger.info("Setting up database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables set up successfully.")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        raise e

    yield

    # Shutdown logic
    logger.info("Shutting down the Investigative AI Data Analyst backend service.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware
# Allowed origins can be configured per environment for higher security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register aggregated routers
app.include_router(api_router, prefix=settings.API_V1_STR)
