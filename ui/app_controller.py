"""
app_controller.py
-----------------
Central workflow coordinator.

Holds page, AppState and pipeline.
Decides which screen is shown.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import AppState, CaseSummary
from services.pipeline_service import PipelineService
from ui.screens.screen_welcome import ScreenWelcome
from ui.screens.screen_interview import ScreenInterview
from ui.screens.screen_summary_review import ScreenSummaryReview
from ui.screens.screen_composer import ScreenComposer


class AppController:

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = AppState()
        self._pipeline = PipelineService().build()

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

    def show_screen_3(self, summary: CaseSummary) -> None:
        self.state.current_screen = 3
        self.state.summary = summary
        self.page.controls.clear()
        ScreenComposer(self.page, self._pipeline, summary).render()
        self.page.update()
