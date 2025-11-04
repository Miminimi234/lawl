"""
Pydantic schemas for case API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.case import CaseStatus


class CaseBase(BaseModel):
    title: str = Field(..., description="Case caption or title")
    jurisdiction: Optional[str] = Field(None, description="Court or jurisdiction")
    case_type: Optional[str] = Field(None, description="Legal category")
    facts: Optional[str] = Field(None, description="Narrative statement of facts")
    legal_arguments: Optional[str] = None
    evidence_summary: Optional[str] = None
    plaintiff_claims: Optional[str] = None
    defendant_defenses: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    submitted_by: Optional[str] = None
    parties_involved: Optional[Dict[str, Any]] = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    jurisdiction: Optional[str] = None
    case_type: Optional[str] = None
    facts: Optional[str] = None
    legal_arguments: Optional[str] = None
    evidence_summary: Optional[str] = None
    plaintiff_claims: Optional[str] = None
    defendant_defenses: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    submitted_by: Optional[str] = None
    parties_involved: Optional[Dict[str, Any]] = None
    status: Optional[CaseStatus] = None
    recommendation: Optional[str] = None
    confidence_score: Optional[float] = None
    analysis_result: Optional[Dict[str, Any]] = None


class CaseResponse(BaseModel):
    id: int
    case_number: str
    title: str
    jurisdiction: Optional[str]
    case_type: Optional[str]
    facts: Optional[str]
    legal_arguments: Optional[str]
    evidence_summary: Optional[str]
    plaintiff_claims: Optional[str]
    defendant_defenses: Optional[str]
    plaintiff: Optional[str]
    defendant: Optional[str]
    submitted_by: Optional[str]
    parties_involved: Optional[Dict[str, Any]]
    status: CaseStatus
    recommendation: Optional[str]
    confidence_score: Optional[float]
    analysis_result: Optional[Dict[str, Any]]
    analyzed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    cases: List[CaseResponse]
