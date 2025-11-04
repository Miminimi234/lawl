"""
Pydantic models for the counsel chat API.
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    """Past exchange in the counsel chat."""

    role: Literal["user", "assistant"] = Field(
        ...,
        description="Speaker role as expected by OpenAI",
    )
    content: str = Field(..., description="Message content")


class CounselRequest(BaseModel):
    """Request payload sent by the frontend counsel chat."""

    message: str = Field(..., min_length=1, description="Latest user message")
    history: List[ChatHistoryMessage] = Field(
        default_factory=list,
        description="Chronological chat history (oldest to newest)",
    )


class JudgeOpinion(BaseModel):
    """Single judge opinion returned by the AI panel."""

    judge: str = Field(..., description="Judge name")
    specialty: str = Field(..., description="Judge specialization")
    opinion: str = Field(..., description="Narrative opinion text")


class CounselResponse(BaseModel):
    """Structured response consumed by the frontend."""

    response: str = Field(..., description="High-level panel summary")
    judges: List[JudgeOpinion] = Field(
        default_factory=list,
        description="Detailed opinions from each judge",
    )
