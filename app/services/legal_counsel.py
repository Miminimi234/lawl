"""
Legal counsel service powered by OpenAI panel responses.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from openai import AsyncOpenAI, OpenAIError  # type: ignore
except ModuleNotFoundError:
    AsyncOpenAI = None  # type: ignore

    class OpenAIError(Exception):
        """Fallback error when OpenAI SDK is unavailable."""

from app.core.config import settings

logger = logging.getLogger(__name__)


class CounselServiceError(Exception):
    """Base class for counsel-related errors."""


class CounselConfigurationError(CounselServiceError):
    """Raised when required configuration is missing or invalid."""


class CounselSessionNotFound(CounselServiceError):
    """Raised when a counsel session cannot be located."""


DEFAULT_PANEL = [
    {"judge": "Judge Morrison", "specialty": "Constitutional & Appellate Law"},
    {"judge": "Judge Chen", "specialty": "Corporate & Contract Law"},
    {"judge": "Judge Rodriguez", "specialty": "Civil Rights & Criminal Procedure"},
]

SYSTEM_PROMPT = (
    "You are the VERDICT Judicial Panel, a collective of three AI judges providing legal guidance.\n"
    "Always reason carefully, reference applicable U.S. law where possible, and acknowledge uncertainty when facts are thin.\n"
    "Respond in valid JSON with the structure:\n"
    "{\n"
    '  "panel_summary": "...",\n'
    '  "judges": [\n'
    '    {"judge": "...", "specialty": "...", "opinion": "..."}\n'
    "  ],\n"
    '  "citations": ["..."]\n'
    "}\n"
    "If you must ask a clarifying question, do so via the panel_summary field."
)


@dataclass
class CounselSession:
    """Represents an in-memory counsel session."""

    session_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)


class LegalCounselService:
    """Manages counsel sessions and delegates to OpenAI."""

    def __init__(self) -> None:
        self._sessions: Dict[str, CounselSession] = {}
        self._lock = asyncio.Lock()
        self._client: Optional[AsyncOpenAI] = None

    def is_available(self) -> bool:
        """Check whether the OpenAI-backed counsel service can run."""
        if AsyncOpenAI is None:
            return False
        return bool(settings.OPENAI_API_KEY)

    def _ensure_client(self) -> Any:
        if AsyncOpenAI is None:
            logger.error("OpenAI Python SDK is not installed for legal counsel service")
            raise CounselConfigurationError("OpenAI Python SDK is not installed.")
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("OpenAI API key missing for legal counsel service")
            raise CounselConfigurationError("OpenAI API key is not configured.")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=api_key)
        return self._client

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        session = CounselSession(session_id=session_id)
        session.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        async with self._lock:
            self._sessions[session_id] = session
        logger.debug("Created counsel session %s", session_id)
        return session_id

    async def _get_session_copy(self, session_id: str) -> List[Dict[str, str]]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                logger.warning("Counsel session %s not found", session_id)
                raise CounselSessionNotFound(f"Session {session_id} not found.")
            # Return a shallow copy so we don't mutate during generation
            return list(session.messages)

    async def _append_messages(self, session_id: str, *messages: Dict[str, str]) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise CounselSessionNotFound(f"Session {session_id} not found.")
            session.messages.extend(messages)

    async def ask_question(
        self,
        session_id: str,
        case_title: str,
        facts: Optional[str],
        question: str,
        jurisdiction: Optional[str] = None,
        case_type: Optional[str] = None,
    ) -> Dict[str, object]:
        logger.info(
            "Counsel ask: session=%s title=%s jurisdiction=%s case_type=%s question_len=%s facts_len=%s",
            session_id,
            (case_title or "")[:60],
            jurisdiction,
            case_type,
            len(question or ""),
            len(facts or "") if facts else 0,
        )

        conversation = await self._get_session_copy(session_id)
        client = self._ensure_client()

        user_prompt = self._build_prompt(case_title, facts, question, jurisdiction, case_type)
        conversation.append({"role": "user", "content": user_prompt})

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL or "gpt-4o-mini",
                messages=conversation,
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                response_format={"type": "json_object"},
            )
        except OpenAIError as exc:
            logger.exception("OpenAI chat completion failed: %s", exc)
            raise CounselServiceError("OpenAI completion failed") from exc
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.exception("Counsel ask unexpected failure: %s", exc)
            raise CounselServiceError("Counsel service encountered an unexpected error.") from exc

        if not response.choices:
            raise CounselServiceError("No response returned from OpenAI.")

        message_content = response.choices[0].message.content or ""
        parsed = self._parse_response(message_content)

        await self._append_messages(
            session_id,
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": self._history_snippet(parsed)},
        )

        return {
            "session_id": session_id,
            "answer": parsed["panel_summary"],
            "judges": parsed["judges"],
            "citations": parsed.get("citations", []),
        }

    def _build_prompt(
        self,
        case_title: str,
        facts: Optional[str],
        question: str,
        jurisdiction: Optional[str],
        case_type: Optional[str],
    ) -> str:
        sections = [
            f"Case Title: {case_title.strip() or 'General Consultation'}",
            f"Question: {question.strip()}",
        ]
        if jurisdiction:
            sections.append(f"Jurisdiction: {jurisdiction.strip()}")
        if case_type:
            sections.append(f"Case Type: {case_type.strip()}")
        if facts:
            sections.append("Facts:\n" + facts.strip())
        return "\n\n".join(sections)

    def _parse_response(self, content: str) -> Dict[str, object]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse counsel response as JSON; falling back to plain text.")
            payload = {
                "panel_summary": content.strip() or "No analysis was generated.",
                "judges": [],
                "citations": [],
            }

        panel_summary = str(payload.get("panel_summary") or "").strip()
        if not panel_summary:
            panel_summary = "I could not generate an opinion with the provided information."

        judges_payload = payload.get("judges") or []
        normalized: List[Dict[str, str]] = []
        for idx, judge_info in enumerate(judges_payload):
            judge_name = str(judge_info.get("judge") or "").strip()
            specialty = str(judge_info.get("specialty") or "").strip()
            opinion = str(judge_info.get("opinion") or "").strip()
            if not opinion:
                continue
            if not judge_name and idx < len(DEFAULT_PANEL):
                judge_name = DEFAULT_PANEL[idx]["judge"]
            if not specialty and idx < len(DEFAULT_PANEL):
                specialty = DEFAULT_PANEL[idx]["specialty"]
            normalized.append(
                {
                    "judge": judge_name or f"Panel Judge {idx + 1}",
                    "specialty": specialty,
                    "opinion": opinion,
                }
            )

        if not normalized:
            normalized = [
                {**judge, "opinion": panel_summary} for judge in DEFAULT_PANEL
            ]

        citations = payload.get("citations") or []

        return {
            "panel_summary": panel_summary,
            "judges": normalized,
            "citations": citations,
        }

    def _history_snippet(self, parsed: Dict[str, object]) -> str:
        lines = [parsed["panel_summary"]]
        for judge in parsed["judges"]:
            specialty = judge.get("specialty", "").strip()
            if specialty:
                lines.append(f"{judge['judge']} ({specialty}): {judge['opinion']}")
            else:
                lines.append(f"{judge['judge']}: {judge['opinion']}")
        citations = parsed.get("citations") or []
        if citations:
            lines.append("Citations: " + ", ".join(citations))
        return "\n\n".join(lines)


legal_counsel_service = LegalCounselService()
