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

_BG_IMAGE_SRC = "images/pozadi_bambus.png"
_BG_OPACITY   = 0.20
_PAGE_PADDING = 24


class AppController:

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = AppState()

        self._setup_page()
        self.show_screen_1()

    def _setup_page(self) -> None:
        self.page.title = "AUFNAHME TCM KLINIK"
        # Padding and scroll are managed at the wrapper level so the background
        # Container can fill the full window unobstructed.
        self.page.padding = 0
        self.page.scroll = None

    def _wrap_with_background(self) -> None:
        """
        Wrap the screen content in a full-window Container with the bamboo
        background image.

        Why page.padding=0 + page.scroll=None here:
          - scroll=AUTO places content in a ScrollView; expand=True inside a
            ScrollView only grows to content height, not window height.
            Removing page-level scroll lets expand=True fill the full window.
            All complex screens already scroll internally.
          - padding=0 on the page lets the background Container reach the window
            edges. The original 24px page padding is applied as padding on the
            inner content wrapper instead, so visual layout is unchanged.
        """
        controls = list(self.page.controls)
        if not controls:
            return
        # Screens add one root control (a Column).
        # Welcome adds several flat controls — wrap those in a Column.
        content = (
            controls[0]
            if len(controls) == 1
            else ft.Column(controls, spacing=0)
        )
        self.page.controls.clear()
        self.page.controls.append(
            ft.Container(
                # Inner wrapper restores the original 24px page padding.
                content=ft.Container(content=content, padding=_PAGE_PADDING),
                image=ft.DecorationImage(
                    src=_BG_IMAGE_SRC,
                    fit=ft.ImageFit.COVER,
                    opacity=_BG_OPACITY,
                ),
                bgcolor=ft.Colors.WHITE,
                expand=True,
            )
        )

    def show_screen_1(self) -> None:
        self.state.current_screen = 1
        self.page.controls.clear()
        ScreenWelcome(self.page, self).render()
        self._wrap_with_background()
        self.page.update()

    def show_screen_2(self) -> None:
        self.state.current_screen = 2
        self.page.controls.clear()
        ScreenInterview(self.page, self, prefill=self.state.summary).render()
        self._wrap_with_background()
        self.page.update()

    def show_screen_2b(self, summary: CaseSummary) -> None:
        self.state.current_screen = "summary_review"
        self.state.summary = summary
        # Clear stale cluster selection so Summary Review infers from the current
        # case context instead of carrying over a cluster from a previous pass.
        self.state.selected_cluster_id = ""
        self.page.controls.clear()
        ScreenSummaryReview(self.page, self).render()
        self._wrap_with_background()
        self.page.update()

    def show_pilot_composer(
        self,
        summary: CaseSummary | None = None,
        storage_key: str | None = None,
        cumulative_text: str = "",
    ) -> None:
        """
        Production composer — unified cluster architecture.

        Entry points:
          a) show_pilot_composer(summary, storage_key=...)  — from SummaryReview
          b) show_pilot_composer()                          — direct access (no interview)
          c) show_pilot_composer(summary, storage_key=..., cumulative_text=...)
             — block continuation: pre-seeds Arbeitstext with already accepted text

        storage_key is stored in state.selected_cluster_id and passed to
        ScreenPilotComposer.  When None, the composer falls back to the
        previously selected cluster or LWS (direct-access path only).
        cumulative_text is passed directly to ScreenPilotComposer and is not
        stored in AppState (it is cluster-agnostic carry-over, not persisted state).
        """
        from ui.screens.screen_pilot_composer import ScreenPilotComposer
        self.state.current_screen = "pilot_composer"
        if summary is not None:
            self.state.summary = summary
        if storage_key:
            self.state.selected_cluster_id = storage_key
        self.page.controls.clear()
        ScreenPilotComposer(
            self.page, self,
            summary=summary,
            storage_key=self.state.selected_cluster_id or None,
            cumulative_text=cumulative_text,
        ).render()
        self._wrap_with_background()
        self.page.update()

    def show_cluster_builder(self, storage_key: str | None = None) -> None:
        from ui.screens.screen_cluster_builder import ScreenClusterBuilder
        self.state.current_screen = "cluster_builder"
        self.page.controls.clear()
        ScreenClusterBuilder(self.page, self, storage_key=storage_key).render()
        self._wrap_with_background()
        self.page.update()
