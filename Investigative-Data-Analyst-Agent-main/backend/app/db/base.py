"""
db/base.py — Import all ORM models so that Base.metadata includes them.
This module must be imported before calling Base.metadata.create_all().
"""
from app.db.session import Base  # noqa: F401
from app.models.dataset import Dataset  # noqa: F401
from app.models.investigation import Investigation, InvestigationDataset  # noqa: F401
from app.models.report import Report  # noqa: F401

