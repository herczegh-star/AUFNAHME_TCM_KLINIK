"""
app_controller.py
-----------------
Central workflow coordinator.

Holds page and AppState.
Decides which screen is shown.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import AppState, CaseSummary
from ui.screens.screen_welcome import ScreenWelcome
from ui.screens.screen_interview import ScreenInterview
from ui.screens.screen_summary_review import ScreenSummaryReview


class AppController:

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = AppState()

        self._setup_page()
        self.show_screen_1()

    def _setup_page(self) -> None:
        self.page.title = "AUFNAHME TCM KLINIK"
        self.page.padding = 24
        self.page.scroll = ft.ScrollMode.AUTO

    def show_screen_1(self) -> None:
        self.state.current_screen = 1
        self.page.controls.clear()
        ScreenWelcome(self.page, self).render()
        self.page.update()

    def show_screen_2(self) -> None:
        self.state.current_screen = 2
        self.page.controls.clear()
        ScreenInterview(self.page, self, prefill=self.state.summary).render()
        self.page.update()

    def show_screen_2b(self, summary: CaseSummary) -> None:
        self.state.current_screen = "summary_review"
        self.state.summary = summary
        self.page.controls.clear()
        ScreenSummaryReview(self.page, self).render()
        self.page.update()

    def show_pilot_composer(self, summary: CaseSummary | None = None) -> None:
        """
        Production composer — unified cluster architecture.

        Entry points:
          a) show_pilot_composer(summary)  — from interview workflow
          b) show_pilot_composer()         — direct access (no interview)
        """
        from ui.screens.screen_pilot_composer import ScreenPilotComposer
        self.state.current_screen = "pilot_composer"
        if summary is not None:
            self.state.summary = summary
        self.page.controls.clear()
        ScreenPilotComposer(self.page, self, summary=summary).render()
        self.page.update()

    def show_cluster_builder(self, storage_key: str | None = None) -> None:
        from ui.screens.screen_cluster_builder import ScreenClusterBuilder
        self.state.current_screen = "cluster_builder"
        self.page.controls.clear()
        ScreenClusterBuilder(self.page, self, storage_key=storage_key).render()
        self.page.update()
