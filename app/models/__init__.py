"""
Expose ORM models for metadata discovery.
"""
from app.db.database import Base  # re-export Base for convenience
from .case import Case, CaseStatus
from .document import Document, DocumentType

__all__ = [
    "Base",
    "Case",
    "CaseStatus",
    "Document",
    "DocumentType",
]
