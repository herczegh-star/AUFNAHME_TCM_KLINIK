"""
agent_mode_service.py
---------------------
LLM service for AI-Agent-Modus.

Provides two transformation steps:
  LLM 1: raw_draft  → structured_draft  (extract + structure clinical facts)
  LLM 2: structured → final_text        (language polish — to be added)

Uses OpenAI SDK (gpt-4o-mini), same pattern as OpenAIRefinerClient.
Falls back to raw input on any error — never crashes the UI.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


_STRUCTURING_SYSTEM = """\
Du bist ein klinischer Dokumentationsassistent.

Aufgabe:
Extrahiere aus dem gegebenen Rohtext ausschließlich die tatsächlich enthaltenen klinisch relevanten Informationen.

Regeln:
- KEINE neuen Informationen hinzufügen
- KEINE Interpretation
- KEINE Diagnosen formulieren
- KEINE Vermutungen
- KEINE Ergänzungen
- Wenn etwas nicht im Text steht, darf es NICHT erscheinen

Strukturiere die Information in kurzer, klarer Form, z. B.:
- Lokalisation
- Ausstrahlung
- Dauer
- Charakter
- Verstärkung
- Linderung
- Begleitsymptome

Nur verwenden, was im Text explizit vorhanden ist.

Antwortformat:
Kurze strukturierte Stichpunkte oder kurze präzise Sätze.
Keine Einleitung, keine Erklärung.\
"""


class AgentModeService:

    MODEL      = "gpt-4o-mini"
    MAX_TOKENS = 1024

    def __init__(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        except Exception as exc:
            print(f"[AgentModeService] client init failed: {exc}")
            self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def raw_to_structured(self, raw_draft: str, section_label: str) -> str:
        """
        LLM 1: Extract and structure clinical facts from raw_draft.
        Falls back to raw_draft if LLM is unavailable or call fails.
        """
        if not raw_draft.strip():
            return raw_draft

        user = f"Bereich: {section_label}\n\nRohtext:\n{raw_draft}"

        try:
            result = self._call_llm(_STRUCTURING_SYSTEM, user)
            return result if result.strip() else raw_draft
        except Exception as exc:
            print(f"[AgentModeService] raw_to_structured failed: {exc}")
            return raw_draft

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _call_llm(self, system: str, user: str) -> str:
        if self._client is None:
            raise RuntimeError("OpenAI client not available (missing SDK or API key).")
        response = self._client.chat.completions.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()
