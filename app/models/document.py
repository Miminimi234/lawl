"""
SQLAlchemy model for stored legal documents.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    String,
    Text,
)

from app.db.database import Base


class DocumentType(str, Enum):
    CASE_LAW = "case_law"
    MEMORANDUM = "memorandum"
    BRIEF = "brief"
    OTHER = "other"


class Document(Base):
    """ORM model storing case-related documents that feed the RAG engine."""

    __tablename__ = "documents"

    id: int = Column(Integer, primary_key=True, index=True)
    title: str = Column(String(512), nullable=False)
    document_type: DocumentType = Column(
        SAEnum(DocumentType), nullable=False, default=DocumentType.CASE_LAW
    )
    citation: Optional[str] = Column(String(256), index=True)
    case_name: Optional[str] = Column(String(512))
    court: Optional[str] = Column(String(256))
    jurisdiction: Optional[str] = Column(String(256))

    summary: Optional[str] = Column(Text)
    full_text: Optional[str] = Column(Text)
    source_url: Optional[str] = Column(String(512))
    weaviate_id: Optional[str] = Column(String(128))

    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
