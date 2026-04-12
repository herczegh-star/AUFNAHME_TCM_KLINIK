"""
screen_welcome.py
-----------------
Screen 1 — Welcome screen.
Generates the Aufnahme-Schablone and navigates to Screen 2.
"""

from __future__ import annotations

import flet as ft

from services.schablone_service import SchabloneService
from ui.theme import _C_OK, _C_ERR, _C_ACCENT


class ScreenWelcome:

    def __init__(self, page: ft.Page, controller) -> None:
        self._page = page
        self._controller = controller

    def render(self) -> None:
        page = self._page
        controller = self._controller

        status_text = ft.Text("", size=13, color=_C_OK)

        # Navigation buttons — visible only after Schablone is generated
        nav_row = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "Weiter zum Interview",
                    icon=ft.Icons.ARROW_FORWARD,
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: controller.show_screen_2(),
                ),
                ft.OutlinedButton(
                    "Direkt zum Pilot-Composer",
                    icon=ft.Icons.SCIENCE_OUTLINED,
                    style=ft.ButtonStyle(color=_C_ACCENT),
                    on_click=lambda e: controller.show_pilot_composer(),
                    tooltip="Pilot-Composer ohne Interview — Formular direkt ausfüllen",
                ),
            ],
            spacing=12,
            visible=False,
        )

        def on_generate(e: ft.ControlEvent) -> None:
            try:
                path = SchabloneService().generate_and_save()
                controller.state.schablone_path = path
                controller.state.schablone_generated = True
                status_text.value = f"Schablone wurde generiert und gespeichert:\n{path.name}"
                nav_row.visible = True
            except Exception as exc:
                status_text.value = f"Fehler: {exc}"
                status_text.color = _C_ERR
            page.update()

        illustration = ft.Image(
            src="images/silueta.png",
            width=360,
            fit=ft.ImageFit.CONTAIN,
            opacity=0.85,
        )

        page.add(
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD, color=_C_ACCENT),
                            ft.Container(height=8),
                            ft.Text("Willkommen", size=18, color=_C_ACCENT),
                            ft.Container(height=16),
                            ft.Container(content=illustration, padding=ft.padding.only(left=60)),
                            ft.Container(height=20),
                            ft.ElevatedButton(
                                "Aufnahme-Schablone generieren",
                                bgcolor=_C_ACCENT,
                                color=ft.Colors.WHITE,
                                on_click=on_generate,
                            ),
                            ft.Container(height=12),
                            status_text,
                            ft.Container(height=12),
                            nav_row,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )
