"""
app_controller.py
-----------------
Central workflow coordinator.

Holds page, AppState and pipeline.
Decides which screen is shown.

Phase 2: only ScreenComposer is wired in.
Phase 3: show_screen_1() and show_screen_2() will be added here.
"""

import flet as ft

from models.case_summary import AppState
from services.pipeline_service import PipelineService
from ui.screens.screen_composer import ScreenComposer


class AppController:

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = AppState()
        self._pipeline = PipelineService().build()

        self._setup_page()
        self._show_composer()

    def _setup_page(self) -> None:
        self.page.title = "AUFNAHME TCM KLINIK"
        self.page.padding = 24
        self.page.scroll = ft.ScrollMode.AUTO

    def _show_composer(self) -> None:
        self.state.current_screen = 3
        ScreenComposer(self.page, self._pipeline).render()
