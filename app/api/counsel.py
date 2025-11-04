"""API endpoints for the VERDICT counsel panel."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.legal_counsel import (
    CounselConfigurationError,
    CounselServiceError,
    CounselSessionNotFound,
    legal_counsel_service,
)

router = APIRouter()


class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the counsel session")


@router.post("/session", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_counsel_session() -> CreateSessionResponse:
    """Create a new counsel session."""
    session_id = await legal_counsel_service.create_session()
    return CreateSessionResponse(session_id=session_id)


class AskCounselRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    case_title: str = ""
    facts: Optional[str] = None
    question: str = Field(..., min_length=3)
    jurisdiction: Optional[str] = None
    case_type: Optional[str] = None


class JudgeOpinion(BaseModel):
    judge: str
    specialty: str
    opinion: str


class AskCounselResponse(BaseModel):
    session_id: str
    answer: str
    judges: List[JudgeOpinion]
    citations: List[str] = []


@router.post("/ask", response_model=AskCounselResponse)
async def ask_counsel(payload: AskCounselRequest) -> AskCounselResponse:
    """Submit a question to the counsel session and receive panel guidance."""
    try:
        result = await legal_counsel_service.ask_question(
            session_id=payload.session_id,
            case_title=payload.case_title or "",
            facts=payload.facts,
            question=payload.question,
            jurisdiction=payload.jurisdiction,
            case_type=payload.case_type,
        )
    except CounselSessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CounselConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except CounselServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AskCounselResponse(**result)
