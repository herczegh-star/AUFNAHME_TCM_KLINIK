"""
prompt_builder.py
-----------------
Builds system and user prompts for the AI draft mode pipeline.

No LLM calls. No UI. No side effects.
"""

from __future__ import annotations

from core.draft_schema import ClusterStyleConfig, SymptomDraftInput


def _join_or_dash(values: list[str]) -> str:
    return ", ".join(v for v in values if v) or "-"


def _val(value: str | None) -> str:
    return value.strip() if value and value.strip() else "-"


class PromptBuilder:

    def build_system_prompt(self) -> str:
        return (
            "Du bist ein klinischer Dokumentationsassistent. "
            "Deine einzige Aufgabe ist es, aus strukturierten Patientendaten "
            "einen klinischen Freitext im Verdichtungsstil zu formulieren.\n\n"
            "Strenge Regeln:\n"
            "- Du fügst keine neuen Fakten hinzu, die nicht in den Eingabedaten stehen.\n"
            "- Du stellst keine Diagnosen und interpretierst keine unausgesprochenen Informationen.\n"
            "- Du gibst keine Therapieempfehlungen.\n"
            "- Du schreibst klinisch-sachlich, stets im Präsens.\n"
            "- Du schreibst stets im Verdichtungsstil: kompakt, ohne Füllwörter, ohne Floskeln.\n"
            "- Du fügst keine Kommentare, Erläuterungen oder Überschriften in den Text ein.\n"
            "- Du spekulierst nicht über fehlende Informationen.\n"
            "- Wenn eine Information nicht angegeben ist, lässt du sie vollständig weg.\n"
        )

    def build_user_prompt(
        self,
        draft_input: SymptomDraftInput,
        style_config: ClusterStyleConfig,
    ) -> str:
        lines: list[str] = []

        # --- CLUSTER ---
        lines.append("=== CLUSTER ===")
        lines.append(draft_input.cluster)
        lines.append("")

        # --- STRUKTURIERTE FAKTEN ---
        lines.append("=== STRUKTURIERTE FAKTEN ===")
        lines.append(f"Cluster:                  {draft_input.cluster}")
        lines.append(f"Dauer:                    {_val(draft_input.duration)}")
        lines.append(f"Lokalisation:             {_val(draft_input.localisation)}")
        lines.append(f"Seite:                    {_val(draft_input.side)}")
        lines.append(f"Schmerzcharakter:         {_join_or_dash(draft_input.pain_quality)}")
        lines.append(f"Ausstrahlung:             {_val(draft_input.radiation)}")
        lines.append(f"Verschlechterungsfakt.:   {_join_or_dash(draft_input.aggravating_factors)}")
        lines.append(f"Linderungsfaktoren:       {_join_or_dash(draft_input.relieving_factors)}")
        lines.append(f"Funktionelle Einschr.:    {_join_or_dash(draft_input.functional_limitations)}")
        lines.append(f"Zusatzhinweise:           {_val(draft_input.additional_notes)}")
        lines.append("")

        # --- STILREGELN ---
        lines.append("=== STILREGELN ===")
        for rule in style_config.rules:
            lines.append(f"- {rule}")
        lines.append("")

        # --- BEVORZUGTE MUSTER ---
        lines.append("=== BEVORZUGTE MUSTER ===")
        for pattern in style_config.preferred_patterns:
            lines.append(f"- {pattern}")
        lines.append("")

        # --- BEISPIELE ---
        lines.append("=== BEISPIELE ===")
        for i, example in enumerate(style_config.examples[:3], 1):
            lines.append(f"Beispiel {i}:")
            lines.append(example)
            lines.append("")

        # --- AUFGABE ---
        lines.append("=== AUFGABE ===")
        lines.append(
            "Erstelle einen klinischen Dokumentationstext ausschließlich auf Basis "
            "der oben angegebenen strukturierten Fakten.\n"
            "Halte dich dabei an die Stilregeln und bevorzugten Muster.\n\n"
            "Vollständigkeit – Pflichtregeln:\n"
            "- Alle angegebenen Informationen müssen, sofern medizinisch sinnvoll, "
            "im Text berücksichtigt werden. Keine relevanten Eingabefelder dürfen ausgelassen werden.\n"
            "- Wenn funktionelle Einschränkungen angegeben sind, müssen sie im Text erwähnt werden.\n"
            "- Wenn eine Ausstrahlung angegeben ist, muss sie inhaltlich präzise übernommen "
            "und darf nicht vereinfacht werden.\n"
            "- Wenn Zusatzhinweise angegeben sind und sie für die Beschwerdeschilderung relevant sind, "
            "sollen sie knapp integriert werden.\n\n"
            "Weitere Vorgaben:\n"
            "- Verwende nur Informationen aus den strukturierten Fakten.\n"
            "- Füge keine neuen Informationen hinzu.\n"
            "- Stelle keine Diagnosen, gib keine Therapieempfehlungen.\n"
            "- Umfang: 3–4 Sätze.\n"
            "- Keine Kommentare, keine Erläuterungen, keine Überschriften.\n"
            "- Nur der fertige klinische Text."
        )

        return "\n".join(lines)
