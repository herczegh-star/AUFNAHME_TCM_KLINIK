"""
screen_summary_review.py
------------------------
Screen 2b — Summary review step between interview and composer.

Physician can inspect and edit the collected interview answers
before proceeding to the composer.

No AI. No cluster logic. No automatic interpretation.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import CaseSummary


_FIELDS = [
    ("Hauptbeschwerde",                             "most_burdensome"),
    ("Weitere im Vordergrund stehende Beschwerden", "priority_complaint"),
    ("Weitere Beschwerden",                         "additional_complaints"),
]


class ScreenSummaryReview:

    def __init__(self, page: ft.Page, controller) -> None:
        self._page = page
        self._controller = controller

    def render(self) -> None:
        page       = self._page
        controller = self._controller
        summary    = controller.state.summary

        fields = [
            ft.TextField(
                label=label,
                value=getattr(summary, attr),
                multiline=True,
                min_lines=2,
                max_lines=4,
                expand=True,
            )
            for label, attr in _FIELDS
        ]

        def on_weiter(e: ft.ControlEvent) -> None:
            updated = CaseSummary(
                main_complaints       = summary.main_complaints,
                most_burdensome       = fields[0].value.strip(),
                priority_complaint    = fields[1].value.strip(),
                additional_complaints = fields[2].value.strip(),
            )
            controller.show_screen_3(updated)

        def on_zurueck(e: ft.ControlEvent) -> None:
            controller.show_screen_2()

        page.add(
            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),
            ft.Text("Fallübersicht prüfen", size=16),
            ft.Container(height=16),
            *fields,
            ft.Container(height=16),
            ft.Row(
                controls=[
                    ft.OutlinedButton("Zurück zum Interview", on_click=on_zurueck),
                    ft.ElevatedButton("Weiter zum Composer", on_click=on_weiter),
                ],
                spacing=12,
            ),
        )
