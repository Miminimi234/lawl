"""
SQLAlchemy model for legal cases.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.database import Base


class CaseStatus(str, Enum):
    """Lifecycle of a case inside the system."""

    SUBMITTED = "submitted"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    ERROR = "error"
    ARCHIVED = "archived"


class Case(Base):
    """ORM representation of a tracked case."""

    __tablename__ = "cases"

    id: int = Column(Integer, primary_key=True, index=True)
    case_number: str = Column(String(128), unique=True, nullable=False, index=True)
    title: str = Column(String(512), nullable=False)

    plaintiff: Optional[str] = Column(String(256))
    defendant: Optional[str] = Column(String(256))
    submitted_by: Optional[str] = Column(String(256))

    facts: Optional[str] = Column(Text)
    case_facts: Optional[str] = Column(Text)  # legacy compatibility
    legal_arguments: Optional[str] = Column(Text)
    evidence_summary: Optional[str] = Column(Text)
    plaintiff_claims: Optional[str] = Column(Text)
    defendant_defenses: Optional[str] = Column(Text)

    jurisdiction: Optional[str] = Column(String(256), index=True)
    case_type: Optional[str] = Column(String(128), index=True)

    parties_involved: Optional[Dict[str, Any]] = Column(JSON)

    status: CaseStatus = Column(SAEnum(CaseStatus), default=CaseStatus.SUBMITTED)
    recommendation: Optional[str] = Column(Text)
    confidence_score: Optional[float] = Column(Float)
    analysis_result: Optional[Dict[str, Any]] = Column(JSON)
    analyzed_at: Optional[datetime] = Column(DateTime)

    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        """Helper for debugging or manual serialization."""
        return {
            "id": self.id,
            "case_number": self.case_number,
            "title": self.title,
            "plaintiff": self.plaintiff,
            "defendant": self.defendant,
            "status": self.status.value if self.status else None,
        }
