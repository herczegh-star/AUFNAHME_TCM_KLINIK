"""
screen_welcome.py
-----------------
Screen 1 — Welcome screen.
Generates the Aufnahme-Schablone and navigates to Screen 2.
"""

from __future__ import annotations

import flet as ft

from services.schablone_service import SchabloneService


class ScreenWelcome:

    def __init__(self, page: ft.Page, controller) -> None:
        self._page = page
        self._controller = controller

    def render(self) -> None:
        page = self._page
        controller = self._controller

        status_text = ft.Text("", size=13, color=ft.Colors.GREEN_700)
        weiter_button = ft.ElevatedButton(
            "Weiter zum Interview",
            on_click=lambda e: controller.show_screen_2(),
            visible=False,
        )

        def on_generate(e: ft.ControlEvent) -> None:
            try:
                path = SchabloneService().generate_and_save()
                controller.state.schablone_path = path
                controller.state.schablone_generated = True
                status_text.value = f"Schablone wurde generiert und gespeichert:\n{path.name}"
                weiter_button.visible = True
            except Exception as exc:
                status_text.value = f"Fehler: {exc}"
                status_text.color = ft.Colors.RED_700
            page.update()

        page.add(
            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=24),
            ft.Text("Willkommen", size=18),
            ft.Container(height=16),
            ft.ElevatedButton(
                "Aufnahme-Schablone generieren",
                on_click=on_generate,
            ),
            ft.Container(height=12),
            status_text,
            ft.Container(height=12),
            weiter_button,
        )
