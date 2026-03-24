"""
summary_panel.py
----------------
Informational side panel displaying CaseSummary on Screen 3.

Read-only. No AI. No pipeline connection. No editing.
Physician uses it as a working compass only.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import CaseSummary


class SummaryPanel:

    def __init__(self, summary: CaseSummary) -> None:
        self._summary = summary

    def build(self) -> ft.Container:
        rows: list[ft.Control] = [
            ft.Text("FALLÜBERSICHT", weight=ft.FontWeight.BOLD, size=13),
        ]

        for label, value in [
            ("Hauptbeschwerde",    self._summary.priority_complaint),
            ("Weitere Angaben",    self._summary.main_complaints),
            ("Belastung",          self._summary.most_burdensome),
            ("Weitere Beschwerden", self._summary.additional_complaints),
        ]:
            if not value:
                continue
            rows.append(ft.Container(height=8))
            rows.append(ft.Text(label, weight=ft.FontWeight.W_600, size=12,
                                color=ft.Colors.GREY_700))
            rows.append(ft.Text(value, size=12, selectable=True))

        return ft.Container(
            width=280,
            padding=16,
            bgcolor=ft.Colors.GREY_100,
            border_radius=8,
            content=ft.Column(controls=rows, spacing=2, scroll=ft.ScrollMode.AUTO),
        )
