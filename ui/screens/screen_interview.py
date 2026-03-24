"""
screen_interview.py
-------------------
Screen 2 — Psychosomatic interview funnel.
Collects 4 answers and creates a raw CaseSummary.
No AI, no embeddings, no clinical interpretation.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import CaseSummary


# (label, hint_text)
_QUESTIONS = [
    (
        "Welche körperlichen Beschwerden stehen aktuell im Vordergrund?",
        "",
    ),
    (
        "Welche dieser Beschwerden steht für Sie aktuell im Vordergrund?",
        "Bitte nur eine Beschwerde auswählen.",
    ),
    (
        "Welche 1–2 weiteren Beschwerden stehen neben dem Hauptproblem aktuell ebenfalls im Vordergrund?",
        "Bitte maximal zwei Beschwerden.",
    ),
    (
        "Welche weiteren behandlungsbedürftigen Beschwerden bestehen darüber hinaus?",
        "Bitte kurz aufzählen, ohne Beschreibung.",
    ),
]


class ScreenInterview:

    def __init__(self, page: ft.Page, controller, prefill: CaseSummary | None = None) -> None:
        self._page = page
        self._controller = controller
        self._prefill = prefill

    def render(self) -> None:
        page       = self._page
        controller = self._controller
        prefill    = self._prefill

        _prefill_values = [
            prefill.main_complaints       if prefill else "",
            prefill.most_burdensome       if prefill else "",
            prefill.priority_complaint    if prefill else "",
            prefill.additional_complaints if prefill else "",
        ]

        fields = [
            ft.TextField(
                label=label,
                value=_prefill_values[i],
                multiline=True,
                min_lines=2,
                max_lines=4,
                expand=True,
            )
            for i, (label, _hint) in enumerate(_QUESTIONS)
        ]

        def _wrap(tf: ft.TextField, hint: str) -> ft.Control:
            if not hint:
                return tf
            return ft.Column(
                controls=[
                    ft.Text(hint, size=11, color=ft.Colors.GREY_600, italic=True),
                    tf,
                ],
                spacing=4,
            )

        field_controls = [
            _wrap(fields[i], hint)
            for i, (_, hint) in enumerate(_QUESTIONS)
        ]

        def on_weiter(e: ft.ControlEvent) -> None:
            summary = CaseSummary(
                main_complaints       = fields[0].value.strip(),
                most_burdensome       = fields[1].value.strip(),
                priority_complaint    = fields[2].value.strip(),
                additional_complaints = fields[3].value.strip(),
            )
            controller.show_screen_2b(summary)

        page.add(
            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),
            ft.Text("Psychosomatisches Interview", size=16),
            ft.Container(height=16),
            *field_controls,
            ft.Container(height=16),
            ft.ElevatedButton("Weiter", on_click=on_weiter),
        )
