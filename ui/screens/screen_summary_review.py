"""
screen_summary_review.py
------------------------
Screen 2b — Summary review step between interview and composer.

Physician can inspect and edit the collected interview answers
and select the cluster to open in Pilot-Composer before proceeding.

No AI. No automatic cluster matching.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import CaseSummary
from services.unified_cluster_service import list_available_with_names


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

        # --- Cluster selection ---
        available = list_available_with_names()  # list of (storage_key, display_name)

        # Determine initial selection: previously chosen key, or first available
        prev_key = controller.state.selected_cluster_id or ""
        valid_keys = [sk for sk, _ in available]
        initial_key = prev_key if prev_key in valid_keys else (valid_keys[0] if valid_keys else "")

        cluster_dropdown = ft.Dropdown(
            label="Cluster auswählen",
            value=initial_key,
            options=[
                ft.dropdown.Option(key=sk, text=name)
                for sk, name in available
            ],
            width=320,
        )

        def _collect() -> CaseSummary:
            return CaseSummary(
                main_complaints       = summary.main_complaints,
                most_burdensome       = fields[0].value.strip(),
                priority_complaint    = fields[1].value.strip(),
                additional_complaints = fields[2].value.strip(),
            )

        def on_pilot_composer(e: ft.ControlEvent) -> None:
            selected_key = cluster_dropdown.value or initial_key
            controller.show_pilot_composer(_collect(), storage_key=selected_key)

        def on_zurueck(e: ft.ControlEvent) -> None:
            controller.show_screen_2()

        page.add(
            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),
            ft.Text("Fallübersicht prüfen", size=16),
            ft.Container(height=16),
            *fields,
            ft.Container(height=16),
            ft.Column(
                controls=[
                    ft.Text(
                        "Cluster für Pilot-Composer:",
                        size=13,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    cluster_dropdown,
                ],
                spacing=6,
            ),
            ft.Container(height=16),
            ft.Row(
                controls=[
                    ft.OutlinedButton("← Zurück zum Interview", on_click=on_zurueck),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Weiter → Pilot-Composer",
                        icon=ft.Icons.SCIENCE_OUTLINED,
                        bgcolor=ft.Colors.BLUE_700,
                        color=ft.Colors.WHITE,
                        on_click=on_pilot_composer,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
