"""
Legal counsel service that orchestrates multi-judge OpenAI analysis.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from app.core.config import settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - fallback for older openai versions
    OpenAI = None  # type: ignore
    import openai  # type: ignore


class LegalCounselService:
    """Generate judicial panel guidance for the counsel chat experience."""

    PANEL_JUDGES: List[Dict[str, str]] = [
        {
            "judge": "Judge Morrison",
            "specialty": "Constitutional & Appellate Law",
            "focus": (
                "Analyze constitutional implications, appellate standards, "
                "and structural legal doctrines. Highlight controlling precedent, "
                "jurisdictional posture, and constitutional tests that govern."
            ),
        },
        {
            "judge": "Judge Chen",
            "specialty": "Corporate & Contract Law",
            "focus": (
                "Examine commercial relationships, contract formation and breach, "
                "corporate governance duties, and available remedies. Cite landmark "
                "business law authorities and provide risk mitigation guidance."
            ),
        },
        {
            "judge": "Judge Rodriguez",
            "specialty": "Civil Rights & Criminal Procedure",
            "focus": (
                "Evaluate constitutional rights, statutory protections, "
                "and procedural safeguards. Discuss standards of review, "
                "burden shifting, and potential government liability."
            ),
        },
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured for the counsel service.")

        self.model = model or settings.OPENAI_MODEL or "gpt-4o-mini"
        self.temperature = (
            temperature if temperature is not None else min(settings.TEMPERATURE, 0.7)
        )

        # Initialize OpenAI client compatible with both legacy and current SDKs.
        if OpenAI:
            self.client = OpenAI(api_key=self.api_key)
            self._use_responses_api = hasattr(self.client, "responses")
        else:  # pragma: no cover - legacy SDK path
            openai.api_key = self.api_key  # type: ignore[attr-defined]
            self.client = openai  # type: ignore[assignment]
            self._use_responses_api = False

    def generate_panel_guidance(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Produce a structured legal guidance response for the counsel chat.

        Returns:
            dict: {
                "response": str,
                "judges": List[{"judge": str, "specialty": str, "opinion": str}]
            }
        """
        if not message.strip():
            raise ValueError("Message content is required.")

        chat_messages = self._build_conversation(history or [], message)

        try:
            content = self._invoke_model(chat_messages)
            parsed = self._parse_model_output(content)
        except Exception:
            raise

        return {
            "response": parsed.get(
                "panel_summary",
                "The judicial panel considered your submission but the summary "
                "could not be generated at this time.",
            ),
            "judges": parsed.get("judges", []),
        }

    def _build_conversation(
        self,
        history: List[Dict[str, str]],
        latest_message: str,
    ) -> List[Dict[str, str]]:
        """Transform UI history into OpenAI chat messages with panel context."""
        system_intro = (
            "You are VERDICT, a three-judge appellate panel that delivers rigorous, "
            "cited legal guidance. ALWAYS respond with a valid JSON object matching "
            "this schema:\n"
            "{\n"
            '  "panel_summary": "<short panel-wide summary>",\n'
            '  "judges": [\n'
            '    {"judge": "Judge Morrison", "specialty": "...", "opinion": "..."},\n'
            '    {"judge": "Judge Chen", "specialty": "...", "opinion": "..."},\n'
            '    {"judge": "Judge Rodriguez", "specialty": "...", "opinion": "..."}\n'
            "  ]\n"
            "}\n"
            "Each opinion must be 2-3 rich paragraphs that cite notable cases, "
            "statutes, or legal tests. Reference any documents mentioned in the "
            "conversation history, and offer pragmatic next steps."
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_intro}]

        for entry in history:
            role = entry.get("role", "user")
            if role not in {"user", "assistant"}:
                continue
            messages.append(
                {"role": role, "content": entry.get("content", "").strip()}
            )

        panel_brief = self._panel_brief()
        messages.append(
            {
                "role": "system",
                "content": panel_brief,
            }
        )

        messages.append({"role": "user", "content": latest_message.strip()})
        return messages

    def _panel_brief(self) -> str:
        """Return descriptive brief about each judge for consistent tone."""
        descriptions = []
        for judge in self.PANEL_JUDGES:
            descriptions.append(
                f"{judge['judge']} ({judge['specialty']}): {judge['focus']}"
            )
        return (
            "Panel composition and expectations:\n- "
            + "\n- ".join(descriptions)
            + "\nRespond sequentially for judges 1-3."
        )

    def _invoke_model(self, messages: List[Dict[str, str]]) -> str:
        """Invoke OpenAI model and return raw content."""
        if self._use_responses_api:  # pragma: no cover - dependent on SDK version
            response = self.client.responses.create(  # type: ignore[attr-defined]
                model=self.model,
                input=messages,
                temperature=self.temperature,
                max_output_tokens=1800,
            )
            return response.output_text  # type: ignore[attr-defined,no-any-return]

        completion = self.client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=1800,
        )
        return completion.choices[0].message.content  # type: ignore[return-value]

    def _parse_model_output(self, content: Optional[str]) -> Dict[str, object]:
        """Parse JSON payload from the model output, handling code fences."""
        if not content:
            return {}

        text = content.strip()
        if text.startswith("```"):
            fence = text.split("\n", 1)[1]
            text = fence.rsplit("```", 1)[0]

        candidate = self._extract_json_segment(text)
        if not candidate:
            return {}

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return {}

        # Ensure judges list has expected keys.
        judges: List[Dict[str, str]] = []
        for judge in parsed.get("judges", []):
            name = judge.get("judge")
            specialty = judge.get("specialty")
            opinion = judge.get("opinion")
            if name and specialty and opinion:
                judges.append(
                    {
                        "judge": name,
                        "specialty": specialty,
                        "opinion": opinion,
                    }
                )

        parsed["judges"] = judges
        return parsed

    @staticmethod
    def _extract_json_segment(text: str) -> Optional[str]:
        """Locate the first JSON object within the provided text."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]


__all__ = ["LegalCounselService"]
