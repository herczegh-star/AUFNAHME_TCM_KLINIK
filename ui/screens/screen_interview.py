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


_QUESTIONS = [
    "Welche körperlichen Beschwerden beschäftigen Sie aktuell?",
    "Was davon belastet Sie im Alltag am meisten?",
    "Wenn Sie eine Beschwerde sofort loswerden könnten – welche wäre das?",
    "Gibt es noch weitere Beschwerden, die wir berücksichtigen sollten?",
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
                label=q,
                value=_prefill_values[i],
                multiline=True,
                min_lines=2,
                max_lines=4,
                expand=True,
            )
            for i, q in enumerate(_QUESTIONS)
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
            *fields,
            ft.Container(height=16),
            ft.ElevatedButton("Weiter", on_click=on_weiter),
        )
