"""
screen_pilot_composer.py
------------------------
Production composer screen — built on the unified Cluster-Pilot architecture.

Replaces the legacy ScreenComposer as the default production path.
Supports two entry modes:
  a) With CaseSummary: from the interview workflow
       Welcome → Interview → SummaryReview → here
     - Shows SummaryPanel (read-only reference)
     - Prefills additional_notes from interview answers
     - Back navigates to SummaryReview
  b) Direct access (no interview): summary=None
     - Form is empty; no side panel
     - Back navigates to Welcome

Draft pipeline: 3 stages
  Stage 1 — Roh-Entwurf   : deterministic (always available)
  Stage 2 — Verfeinerung  : LLM grammar/flow cleanup
  Stage 3 — Verdichtung   : LLM Verdichtungsstil pass
  Stages 2 + 3 are disabled (labelled) when HAS_LLM = False.

Word export: inserts best available draft into the Aufnahme-Schablone.
  Priority: Final > Refined > Raw

Navigation:
  Back (with summary)    → AppController.show_screen_2b(summary)
  Back (without summary) → AppController.show_screen_1()
  Cluster-Editor button  → AppController.show_cluster_builder()
"""

from __future__ import annotations

import json
import flet as ft
from pathlib import Path

from models.case_summary import CaseSummary
from models.unified_cluster import UnifiedCluster
from services.unified_cluster_service import load, load_lws, list_available_with_names, get_display_name
from services.cluster_inference import infer_cluster
import services.pilot_draft_service as _svc
from services.pilot_draft_service import HAS_LLM

_PHRASE_LIBRARY_PATH = Path(__file__).parent.parent.parent / "data" / "phrase_library.json"
_phrase_library_cache: dict | None = None


def _get_phrase_library() -> dict:
    """Load and cache data/phrase_library.json.  Returns {} on any read error."""
    global _phrase_library_cache
    if _phrase_library_cache is None:
        try:
            _phrase_library_cache = json.loads(_PHRASE_LIBRARY_PATH.read_text(encoding="utf-8"))
        except Exception:
            _phrase_library_cache = {}
    return _phrase_library_cache


# Clinically generic templates for "Weitere behandlungsbedürftige Beschwerden".
# Not cluster-specific — kept here rather than in sprachbausteine JSON.
# {items} is replaced at insert time with self._summary.additional_complaints.
_WEITERE_BESCHWERDEN_TEMPLATES: list[str] = [
    "Als weitere behandlungsbedürftige Beschwerden bestehen {items}.",
    "Zusätzlich bestehen behandlungsbedürftige Beschwerden in Form von {items}.",
]


# ---------------------------------------------------------------------------
# Colour palette — imported from central theme module
# ---------------------------------------------------------------------------
from ui.theme import (
    _C_BORDER,
    _C_ACCENT,
    _C_ACCENT_ACTIVE,
    _C_WARN,
    _C_OK,
    _C_ERR,
    _C_BG_PANEL,
    _C_BG_MAIN,
    _C_BG_WARN,
    _C_TEXT_SECONDARY,
    _C_TEXT_HELPER,
    _C_IN_PROGRESS,
)


class ScreenPilotComposer:
    """
    Production composer screen.

    Parameters
    ----------
    page       : Flet Page
    controller : AppController
    summary    : CaseSummary or None
        When provided (interview route): prefills additional_notes,
        shows SummaryPanel, back → SummaryReview.
        When None (direct route): empty form, no side panel,
        back → Welcome.
    """

    def __init__(
        self,
        page: ft.Page,
        controller,
        summary: CaseSummary | None = None,
        storage_key: str | None = None,
        cumulative_text: str = "",
    ) -> None:
        self._page           = page
        self._ctrl           = controller
        self._summary        = summary
        self._cumulative_text = cumulative_text
        # Block sequence state — read from AppState at construction time.
        # Empty list means direct-access path or pre-sequence entry (no continuation offered).
        self._block_sequence: list[dict] = list(controller.state.block_sequence)
        self._active_block_index: int    = controller.state.active_block_index
        # Load the explicitly selected cluster when provided.
        # Fall back to LWS only for the direct-access path (no cluster selected yet).
        if storage_key:
            self._cluster: UnifiedCluster = load(storage_key)
        else:
            self._cluster = load_lws()
        self._form_widgets: dict[str, ft.Control] = {}
        self._raw_text     = ""
        self._refined_text = ""
        self._final_text   = ""
        self._composer_state: str = "aufbau"
        # Snapshots saved at state transitions for back-navigation.
        self._snapshot_aufbau:      str = ""
        self._snapshot_bearbeitung: str = ""
        # References to panels stored at render time for visibility toggling.
        self._form_panel_ctrl:     ft.Control | None = None
        self._form_divider_ctrl:   ft.Control | None = None
        self._summary_divider_ctrl: ft.Control | None = None
        self._summary_panel_ctrl:  ft.Control | None = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self) -> None:
        form_panel  = self._build_form_panel()
        draft_panel = self._build_draft_panel()

        # Store panel references so state transitions can toggle visibility.
        self._form_panel_ctrl   = form_panel
        self._form_divider_ctrl = ft.VerticalDivider(width=1, color=_C_BORDER)

        row_controls: list[ft.Control] = [
            form_panel,
            self._form_divider_ctrl,
            draft_panel,
        ]

        if self._summary:
            from ui.components.summary_panel import SummaryPanel
            self._summary_divider_ctrl  = ft.VerticalDivider(width=1, color=_C_BORDER)
            self._summary_panel_ctrl    = SummaryPanel(self._summary).build()
            row_controls.extend([
                self._summary_divider_ctrl,
                self._summary_panel_ctrl,
            ])

        self._page.add(
            ft.Column(
                controls=[
                    self._build_header(),
                    ft.Divider(height=1, color=_C_BORDER),
                    ft.Row(
                        controls=row_controls,
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        expand=True,
                    ),
                ],
                expand=True,
                spacing=0,
            )
        )
        # Pre-seed Arbeitstext with text carried over from a previous block.
        # Draft restore runs after this and takes precedence only if its storage_key
        # matches the current cluster (which is never the case for block continuation).
        if self._cumulative_text:
            self._raw_text = self._cumulative_text
            self._raw_field.value = self._cumulative_text
            self._connect_btn.disabled = False
            self._refine_btn.disabled = False
            self._insert_btn.disabled = False
            self._status_text.value = "Vorheriger Block übernommen – nächsten Block ergänzen."
            self._status_text.color = _C_OK
            self._page.update()

        # Restore any previously saved draft (in-memory, same session).
        self._restore_draft_if_available()

    # ------------------------------------------------------------------
    # Header row
    # ------------------------------------------------------------------

    def _build_header(self) -> ft.Control:
        if self._summary is not None:
            back_nav = lambda: self._ctrl.show_screen_2b(self._summary)
        else:
            back_nav = lambda: self._ctrl.show_screen_1()

        back_btn = ft.TextButton(
            "← Zurück",
            style=ft.ButtonStyle(color=_C_ACCENT),
            on_click=lambda _: self._guard_leave(back_nav),
        )
        title = ft.Text(
            f"Pilot-Composer: {self._cluster.name}",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=_C_ACCENT,
        )
        builder_btn = ft.OutlinedButton(
            "Cluster-Editor →",
            style=ft.ButtonStyle(color=_C_ACCENT, side=ft.BorderSide(1, _C_ACCENT)),
            on_click=lambda _: self._guard_leave(
                lambda: self._ctrl.show_cluster_builder(
                    storage_key=self._cluster.storage_key
                )
            ),
        )
        return ft.Container(
            content=ft.Row(
                controls=[
                    back_btn,
                    ft.Container(expand=True),
                    title,
                    ft.Container(expand=True),
                    builder_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )

    # ------------------------------------------------------------------
    # Leave guard
    # ------------------------------------------------------------------

    def _guard_leave(self, nav_fn) -> None:
        """
        Guard against accidental navigation away from Pilot-Composer.
        If Arbeitstext is empty: navigate immediately.
        If Arbeitstext has content: show 3-button dialog.
          Abbrechen            → stay
          Speichern und verlassen → save draft to AppState, then navigate
          Ohne Speichern verlassen → navigate without saving
        nav_fn is a zero-argument callable that performs the navigation.
        """
        if not (self._raw_field.value or "").strip():
            nav_fn()
            return

        dlg: ft.AlertDialog

        def _do_save_and_leave(ev) -> None:
            self._page.close(dlg)
            self._save_draft()
            nav_fn()

        def _do_leave(ev) -> None:
            self._page.close(dlg)
            nav_fn()

        def _do_cancel(ev) -> None:
            self._page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Pilot-Composer verlassen?"),
            content=ft.Text(
                "Möchten Sie den Pilot-Composer verlassen? "
                "Sie können den aktuellen Arbeitsstand speichern "
                "oder ohne Speichern verlassen."
            ),
            actions=[
                ft.TextButton("Abbrechen", on_click=_do_cancel),
                ft.TextButton("Speichern und verlassen", on_click=_do_save_and_leave),
                ft.TextButton("Ohne Speichern verlassen", on_click=_do_leave),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.open(dlg)

    def _save_draft(self) -> None:
        """Persist current Arbeitstext and composer state to AppState.pilot_draft."""
        self._ctrl.state.pilot_draft = {
            "text": self._raw_field.value or "",
            "composer_state": self._composer_state,
            "storage_key": self._cluster.storage_key,
        }

    def _restore_draft_if_available(self) -> None:
        """
        Restore a previously saved draft into the visible Arbeitstext field.
        Called at the end of render() after page.add().
        Only restores when the saved draft's storage_key matches the current cluster.
        Clears the draft from AppState after restoring so a second re-entry starts fresh.
        Always restores to aufbau state (safe default on re-entry).
        """
        draft = self._ctrl.state.pilot_draft
        if not draft:
            return
        if draft.get("storage_key") != self._cluster.storage_key:
            return
        text = draft.get("text", "")
        if text:
            self._raw_text = text
            self._raw_field.value = text
            self._connect_btn.disabled = False
            self._refine_btn.disabled = False
            self._insert_btn.disabled = False
            self._status_text.value = "Arbeitsstand wiederhergestellt."
            self._status_text.color = _C_OK
        self._ctrl.state.pilot_draft = None

    # ------------------------------------------------------------------
    # Left panel: form
    # ------------------------------------------------------------------

    def _build_form_panel(self) -> ft.Control:
        fields_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        for field_def in self._cluster.form_fields:
            widget = self._build_field_widget(field_def)
            if widget is not None:
                label = ft.Text(
                    field_def["label"], size=12, color=_C_TEXT_SECONDARY
                )
                fields_col.controls.append(
                    ft.Column([label, widget], spacing=4, tight=True)
                )

        # Prefill from CaseSummary — only after all widgets are created
        if self._summary is not None:
            self._prefill_from_summary(self._summary)

        generate_btn = ft.ElevatedButton(
            "Beschwerdetext generieren",
            icon=ft.Icons.BOLT,
            bgcolor=_C_ACCENT,
            color=ft.Colors.WHITE,
            on_click=self._on_generate_raw,
        )

        # Hint: which form fields are not yet wired into the draft sentence.
        # Driven by cluster JSON: field.active_in_draft (explicit bool) or
        # inferred from shared_items_key != null when the flag is absent.
        _inactive_fields = [
            f["label"]
            for f in self._cluster.form_fields
            if not f.get("active_in_draft", f.get("shared_items_key") is not None)
        ]
        inactive_hint = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=13, color=_C_TEXT_HELPER),
                    ft.Text(
                        f"Noch nicht im Draft: {', '.join(_inactive_fields)}",
                        size=10,
                        color=_C_TEXT_HELPER,
                        italic=True,
                    ),
                ],
                spacing=4,
                wrap=True,
            ),
            visible=bool(_inactive_fields),
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        self._cluster.form_title,
                        size=15,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(height=8),
                    fields_col,
                    ft.Container(height=8),
                    inactive_hint,
                    ft.Container(height=8),
                    generate_btn,
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            width=360,
            padding=16,
            bgcolor=_C_BG_PANEL,
            expand=False,
        )

    def _prefill_from_summary(self, summary: CaseSummary) -> None:
        """
        Prefill form fields from CaseSummary interview answers.

        Mapping:
          additional_notes ← active block's complaint text only.
            Uses block_sequence[active_block_index]["complaint"] when available.
            Falls back to empty when no block sequence is set (direct-access path).

        Block-context isolation: only the complaint belonging to the currently
        composed block is placed here.  priority_complaint and additional_complaints
        from other blocks are NOT mixed in, preventing cross-block contamination.

        Important: no draft is auto-generated here.
        The physician must click "Beschwerdetext generieren" explicitly.
        """
        note_text = ""
        if self._block_sequence:
            idx = self._active_block_index
            if 0 <= idx < len(self._block_sequence):
                note_text = self._block_sequence[idx]["complaint"]

        if note_text:
            widget = self._form_widgets.get("additional_notes")
            if isinstance(widget, ft.TextField):
                widget.value = note_text

    def _build_field_widget(self, field_def: dict) -> ft.Control | None:
        """Build a single form widget for field_def and register it in self._form_widgets."""
        fid   = field_def["id"]
        ftype = field_def.get("type", "text")

        if ftype == "text":
            widget = ft.TextField(
                hint_text=field_def.get("placeholder", ""),
                border_color=_C_BORDER,
                dense=True,
            )
            self._form_widgets[fid] = widget
            return widget

        if ftype == "textarea":
            widget = ft.TextField(
                hint_text=field_def.get("placeholder", ""),
                border_color=_C_BORDER,
                multiline=True,
                min_lines=2,
                max_lines=4,
            )
            self._form_widgets[fid] = widget
            return widget

        if ftype == "select":
            options = [ft.dropdown.Option("—")] + [
                ft.dropdown.Option(o) for o in field_def.get("options", [])
            ]
            widget = ft.Dropdown(
                options=options,
                value="—",
                border_color=_C_BORDER,
                dense=True,
            )
            self._form_widgets[fid] = widget
            return widget

        if ftype == "multi_select":
            chips_row = ft.Row(wrap=True, spacing=6)
            selected: set[str] = set()

            def _make_toggle(opt: str, sel: set):
                def _toggle(e: ft.ControlEvent):
                    if e.control.selected:
                        sel.add(opt)
                    else:
                        sel.discard(opt)
                return _toggle

            for opt in field_def.get("options", []):
                chip = ft.Chip(
                    label=ft.Text(opt, size=11),
                    selected=False,
                    on_select=_make_toggle(opt, selected),
                )
                chips_row.controls.append(chip)

            self._form_widgets[fid] = selected  # type: ignore[assignment]
            return chips_row

        if ftype == "number":
            widget = ft.TextField(
                hint_text=f"{field_def.get('min', 0)}–{field_def.get('max', 10)}",
                border_color=_C_BORDER,
                dense=True,
                keyboard_type=ft.KeyboardType.NUMBER,
                width=80,
            )
            self._form_widgets[fid] = widget
            return widget

        return None  # unknown type — skip silently

    # ------------------------------------------------------------------
    # Right panel: working draft
    # Stage 1: one visible working field (_raw_field).
    # _refined_field and _final_field exist as internal variables only;
    # they are not rendered. Full state-conditional layout comes in Stage 2.
    # ------------------------------------------------------------------

    def _build_draft_panel(self) -> ft.Control:
        self._stage_labels = {
            "raw":     ft.Text("1. Roh-Entwurf",      size=13, weight=ft.FontWeight.W_600, color=_C_TEXT_HELPER),
            "refined": ft.Text("2. Verfeinerung",      size=13, weight=ft.FontWeight.W_600, color=_C_TEXT_HELPER),
            "final":   ft.Text("3. Final-Verdichtung", size=13, weight=ft.FontWeight.W_600, color=_C_TEXT_HELPER),
        }

        self._raw_field = ft.TextField(
            label="Arbeitstext",
            multiline=True, min_lines=8, max_lines=16,
            border_color=_C_BORDER,
            read_only=False,
        )
        self._refined_field = ft.TextField(
            label="Verfeinerter Entwurf",
            multiline=True, min_lines=3, max_lines=6,
            border_color=_C_BORDER,
            read_only=False,
        )
        self._final_field = ft.TextField(
            label="Final-Entwurf (Verdichtungsstil)",
            multiline=True, min_lines=3, max_lines=6,
            border_color=_C_BORDER,
            read_only=False,
        )
        self._status_text = ft.Text("", size=12, color=_C_TEXT_HELPER)

        _connect_label = (
            "Sprachlich verbinden (AI)" if HAS_LLM
            else "Sprachlich verbinden (kein LLM)"
        )
        _refine_label = (
            "Sprachlich glätten (AI)" if HAS_LLM
            else "Sprachlich glätten (kein LLM)"
        )
        _final_label = (
            "Verdichten (AI)" if HAS_LLM
            else "Verdichten (kein LLM)"
        )

        self._connect_btn = ft.OutlinedButton(
            _connect_label,
            icon=ft.Icons.MERGE_TYPE,
            on_click=self._on_connect_blocks,
            disabled=True,
        )
        self._refine_btn = ft.OutlinedButton(
            _refine_label,
            icon=ft.Icons.AUTO_FIX_HIGH,
            on_click=self._on_refine,
            disabled=True,
        )
        self._final_btn = ft.OutlinedButton(
            _final_label,
            icon=ft.Icons.DONE_ALL,
            on_click=self._on_finalize,
            disabled=True,
        )
        self._insert_btn = ft.ElevatedButton(
            "In Schablone einfügen",
            icon=ft.Icons.ADD_TO_PHOTOS,
            bgcolor=_C_OK,
            color=ft.Colors.WHITE,
            on_click=self._on_insert,
            disabled=True,
        )

        no_llm_banner = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=_C_WARN, size=16),
                    ft.Text(
                        "KI nicht verfügbar – Sprachglättung und Verdichtung "
                        "sind manuell möglich.",
                        size=11,
                        color=_C_WARN,
                    ),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            bgcolor=_C_BG_WARN,
            border_radius=4,
            visible=not HAS_LLM,
        )

        ref_section = self._build_ref_texts_section()
        self._ref_section_ctrl = ref_section  # may be None; stored for visibility toggling

        block_row = self._build_block_insertion_row()
        self._block_row_ctrl = block_row

        transition_row = self._build_transition_phrase_row()
        self._transition_row_ctrl = transition_row

        weitere_row = self._build_weitere_beschwerden_row()
        self._weitere_row_ctrl = weitere_row

        continuation_row = self._build_continuation_row()
        self._continuation_row_ctrl = continuation_row

        # --- aufbau-only rows (visible initially) ---
        self._connect_btn_row_ctrl = ft.Row(
            [self._connect_btn],
            alignment=ft.MainAxisAlignment.START,
        )
        self._advance_row_ctrl = ft.Row(
            [
                ft.ElevatedButton(
                    "Aufbau abschliessen →",
                    icon=ft.Icons.ARROW_FORWARD,
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=self._advance_to_bearbeitung,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        # --- bearbeitung-only rows (hidden initially) ---
        self._back_row_ctrl = ft.Row(
            [
                ft.OutlinedButton(
                    "← Zurück zum Aufbau",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=self._return_to_aufbau,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            visible=False,
        )
        self._refine_btn_row_ctrl = ft.Row(
            [self._refine_btn],
            alignment=ft.MainAxisAlignment.END,
            visible=False,
        )
        self._advance_to_ausgabe_row_ctrl = ft.Row(
            [
                ft.ElevatedButton(
                    "Verdichten →",
                    icon=ft.Icons.ARROW_FORWARD,
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=self._advance_to_ausgabe,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
            visible=False,
        )

        # --- ausgabe-only rows (hidden initially) ---
        self._back_to_bearbeitung_row_ctrl = ft.Row(
            [
                ft.OutlinedButton(
                    "← Zurück zur Bearbeitung",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=self._return_to_bearbeitung,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            visible=False,
        )
        self._final_btn_row_ctrl = ft.Row(
            [self._final_btn],
            alignment=ft.MainAxisAlignment.END,
            visible=False,
        )
        self._insert_btn_row_ctrl = ft.Row(
            [self._insert_btn],
            alignment=ft.MainAxisAlignment.END,
            visible=False,
        )

        # Build controls list.
        # Visibility per state is controlled by the transition methods.
        # _refined_field, _final_field and _stage_labels are instance variables
        # for internal compatibility but are never rendered.
        _section_hint = ft.Text(
            "Abschnitt: Derzeitige Beschwerden (somatisch)",
            size=10,
            color=_C_TEXT_HELPER,
            italic=True,
        )

        draft_controls: list[ft.Control] = [
            no_llm_banner,
            ft.Container(height=4),
            self._raw_field,
            _section_hint,
            self._block_row_ctrl,
            self._transition_row_ctrl,
            self._weitere_row_ctrl,
            self._connect_btn_row_ctrl,
            self._advance_row_ctrl,
            self._back_row_ctrl,
            self._refine_btn_row_ctrl,
            self._advance_to_ausgabe_row_ctrl,
            self._back_to_bearbeitung_row_ctrl,
            self._final_btn_row_ctrl,
            ft.Container(height=8),
            self._status_text,
            self._insert_btn_row_ctrl,
            self._continuation_row_ctrl,
        ]
        if ref_section is not None:
            draft_controls.append(ref_section)

        return ft.Container(
            content=ft.Column(
                controls=draft_controls,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=8,
            ),
            padding=16,
            expand=True,
        )

    # ------------------------------------------------------------------
    # Block insertion row (directly below RAW field)
    # ------------------------------------------------------------------

    def _build_block_insertion_row(self) -> ft.Control:
        """
        Introductory phrase picker (Einleitende Formulierung).

        Two-step: type dropdown → phrase dropdown → Einfügen button.
        Inserts the selected phrase at the BEGINNING of Arbeitstext.

        Both intro types read from the shared global phrase_library.json:
          "Neuer Fall"            → new_case_openers.phrases
          "Bekannte/r Patient/in" → returning_patient_openers.phrases

        Not cluster-specific — the library is the single source of truth.
        """
        lib = _get_phrase_library()
        # Phrase lists per intro type — keyed by the type label used in the dropdown.
        self._intro_phrases_by_type: dict[str, list[str]] = {
            "Neuer Fall":            lib.get("new_case_openers",       {}).get("phrases", []),
            "Bekannte/r Patient/in": lib.get("returning_patient_openers", {}).get("phrases", []),
        }

        self._intro_block_dd = ft.Dropdown(
            hint_text="Einleitungstyp wählen …",
            options=[ft.dropdown.Option(k) for k in self._intro_phrases_by_type],
            border_color=_C_BORDER,
            dense=True,
            width=240,
        )

        # Phrase dropdown — shown after a type is selected; options swap per type.
        self._intro_phrase_dd = ft.Dropdown(
            hint_text="Formulierung wählen …",
            options=[],
            border_color=_C_BORDER,
            dense=True,
            expand=True,
            visible=False,
        )

        self._intro_insert_btn = ft.ElevatedButton(
            "Einfügen",
            icon=ft.Icons.VERTICAL_ALIGN_TOP,
            bgcolor=_C_ACCENT,
            color=ft.Colors.WHITE,
            on_click=self._on_intro_insert,
            disabled=True,
        )

        def _on_type_change(e) -> None:
            selected = e.control.value or ""
            phrases = self._intro_phrases_by_type.get(selected, [])
            self._intro_phrase_dd.options = [ft.dropdown.Option(p) for p in phrases]
            self._intro_phrase_dd.value   = None
            self._intro_phrase_dd.visible = bool(selected)
            self._intro_insert_btn.disabled = True
            self._page.update()

        def _on_phrase_change(e) -> None:
            self._intro_insert_btn.disabled = not bool(e.control.value)
            self._page.update()

        self._intro_block_dd.on_change  = _on_type_change
        self._intro_phrase_dd.on_change = _on_phrase_change

        return ft.Column(
            controls=[
                ft.Text(
                    "Einleitende Formulierung",
                    size=11,
                    color=_C_TEXT_SECONDARY,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Row(
                    controls=[
                        self._intro_block_dd,
                        self._intro_phrase_dd,
                        self._intro_insert_btn,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
            tight=True,
        )

    # ------------------------------------------------------------------
    # Transition phrase row (aufbau-only, below intro control)
    # ------------------------------------------------------------------

    def _build_transition_phrase_row(self) -> ft.Control:
        """
        Übergangsformulierung control (aufbau-only).

        Single dropdown populated from the shared global phrase_library.json
        (transition_openers.phrases) + Einfügen button.
        Not cluster-specific.
        Appends the selected phrase to the END of Arbeitstext.
        """
        phrases = _get_phrase_library().get("transition_openers", {}).get("phrases", [])

        self._transition_phrase_dd = ft.Dropdown(
            hint_text="Übergangsformulierung wählen …",
            options=[ft.dropdown.Option(p) for p in phrases],
            border_color=_C_BORDER,
            dense=True,
            expand=True,
        )
        self._transition_insert_btn = ft.ElevatedButton(
            "Einfügen",
            icon=ft.Icons.SUBDIRECTORY_ARROW_RIGHT,
            bgcolor=_C_ACCENT,
            color=ft.Colors.WHITE,
            on_click=self._on_transition_insert,
            disabled=True,
        )

        def _on_phrase_change(e) -> None:
            self._transition_insert_btn.disabled = not bool(e.control.value)
            self._page.update()

        self._transition_phrase_dd.on_change = _on_phrase_change

        return ft.Column(
            controls=[
                ft.Text(
                    "Übergangsformulierung",
                    size=11,
                    color=_C_TEXT_SECONDARY,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Row(
                    controls=[self._transition_phrase_dd, self._transition_insert_btn],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
            tight=True,
        )

    def _on_transition_insert(self, e) -> None:
        """Append the selected transition phrase to the end of Arbeitstext."""
        if not hasattr(self, "_transition_phrase_dd") or not self._transition_phrase_dd.value:
            return
        self._raw_append(self._transition_phrase_dd.value)
        self._status_text.value = "Übergangsformulierung eingefügt."
        self._page.update()

    def _build_weitere_beschwerden_row(self) -> ft.Control:
        """
        "Weitere behandlungsbedürftige Beschwerden" helper row (aufbau-only).

        Visible only when self._summary is set and additional_complaints is non-empty.
        Dropdown offers _WEITERE_BESCHWERDEN_TEMPLATES; Einfügen appends the
        rendered sentence (template with {items} replaced) to Arbeitstext.
        """
        has_items = bool(
            self._summary
            and (self._summary.additional_complaints or "").strip()
        )

        self._weitere_dd = ft.Dropdown(
            hint_text="Formulierung wählen …",
            options=[ft.dropdown.Option(t) for t in _WEITERE_BESCHWERDEN_TEMPLATES],
            border_color=_C_BORDER,
            dense=True,
            expand=True,
        )
        self._weitere_insert_btn = ft.ElevatedButton(
            "Einfügen",
            icon=ft.Icons.SUBDIRECTORY_ARROW_RIGHT,
            bgcolor=_C_ACCENT,
            color=ft.Colors.WHITE,
            on_click=self._on_weitere_insert,
            disabled=True,
        )

        def _on_dd_change(e) -> None:
            self._weitere_insert_btn.disabled = not bool(e.control.value)
            self._page.update()

        self._weitere_dd.on_change = _on_dd_change

        return ft.Column(
            controls=[
                ft.Text(
                    "Weitere behandlungsbedürftige Beschwerden",
                    size=11,
                    color=_C_TEXT_SECONDARY,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Row(
                    controls=[self._weitere_dd, self._weitere_insert_btn],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
            tight=True,
            visible=has_items,
        )

    def _on_weitere_insert(self, e) -> None:
        """Build and append the 'Weitere Beschwerden' sentence to Arbeitstext."""
        if not self._summary:
            return
        template = getattr(self, "_weitere_dd", None)
        if not template or not template.value:
            return
        items_text = (self._summary.additional_complaints or "").strip().rstrip(".")
        if not items_text:
            return
        sentence = template.value.format(items=items_text)
        self._raw_append(sentence)
        self._status_text.value = "Weitere Beschwerden eingefügt."
        self._page.update()

    # ------------------------------------------------------------------
    # Sequential block continuation
    # ------------------------------------------------------------------

    def _build_continuation_row(self) -> ft.Control:
        """
        Inline continuation row shown after a generated block is accepted.

        Appears only when there is a next block in block_sequence
        (i.e. active_block_index + 1 < len(block_sequence)).
        Offers two choices:
          - stay in current block (dismiss row)
          - continue to next block (re-open Pilot-Composer for next cluster)

        If next block has a storage_key (inferred at sequence build time): button shows name.
        If not: inline dropdown for manual cluster selection.

        Always starts visible=False; shown by _on_generation_accepted().
        """
        next_index = self._active_block_index + 1
        if not self._block_sequence or next_index >= len(self._block_sequence):
            # No next block in sequence — return invisible placeholder
            return ft.Container(visible=False, height=0)

        next_block = self._block_sequence[next_index]
        self._next_block_index: int = next_index
        self._next_cluster_key: str = next_block["storage_key"]  # may be "" if not inferred

        stay_btn = ft.TextButton(
            "Im aktuellen Block bleiben",
            style=ft.ButtonStyle(color=_C_TEXT_SECONDARY),
            on_click=self._on_stay_in_block,
        )

        if self._next_cluster_key:
            display_name = get_display_name(self._next_cluster_key)
            row_controls: list[ft.Control] = [
                stay_btn,
                ft.ElevatedButton(
                    f"→ Weiter: {display_name}",
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=self._on_continue_block,
                ),
            ]
        else:
            # No inferred cluster for next block: physician must choose manually
            available = list_available_with_names()
            self._next_cluster_dd = ft.Dropdown(
                hint_text="Cluster für nächsten Block …",
                options=[ft.dropdown.Option(key=sk, text=name) for sk, name in available],
                dense=True,
                width=260,
                border_color=_C_BORDER,
            )
            self._next_continue_btn = ft.ElevatedButton(
                "→ Weiter",
                bgcolor=_C_ACCENT,
                color=ft.Colors.WHITE,
                on_click=self._on_continue_block,
                disabled=True,
            )

            def _on_dd_change(e) -> None:
                self._next_cluster_key = e.control.value or ""
                self._next_continue_btn.disabled = not bool(self._next_cluster_key)
                self._page.update()

            self._next_cluster_dd.on_change = _on_dd_change
            row_controls = [stay_btn, self._next_cluster_dd, self._next_continue_btn]

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Weiter zum nächsten Beschwerdeblock:",
                        size=11,
                        color=_C_TEXT_SECONDARY,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Row(
                        controls=row_controls,
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor=_C_BG_PANEL,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            visible=False,
        )

    def _on_generation_accepted(self) -> None:
        """Called after generated text is accepted into Arbeitstext via _on_generate_raw.
        Shows the continuation row if a next block exists in block_sequence.
        Not triggered by reference text Übernehmen — only by generate-raw path.
        """
        next_index = self._active_block_index + 1
        if not self._block_sequence or next_index >= len(self._block_sequence):
            return
        self._continuation_row_ctrl.visible = True
        self._page.update()

    def _on_stay_in_block(self, e) -> None:
        """Dismiss the continuation row — physician stays in the current cluster."""
        self._continuation_row_ctrl.visible = False
        self._page.update()

    def _on_continue_block(self, e) -> None:
        """Re-open Pilot-Composer for the next complaint block.
        Marks the current block as accepted, advances active_block_index in AppState,
        and carries accepted Arbeitstext forward as cumulative_text.
        Physician's next-cluster choice (inferred or manual) is used as storage_key.
        """
        # Mark current block accepted in the shared sequence
        if self._block_sequence and 0 <= self._active_block_index < len(self._block_sequence):
            self._block_sequence[self._active_block_index]["accepted"] = True
            self._ctrl.state.block_sequence = self._block_sequence
        # Advance index in AppState so next ScreenPilotComposer reads the correct block
        next_index = self._active_block_index + 1
        self._ctrl.state.active_block_index = next_index
        cumulative = self._raw_field.value or ""
        self._ctrl.show_pilot_composer(
            summary=self._summary,
            storage_key=self._next_cluster_key or None,
            cumulative_text=cumulative,
        )

    # ------------------------------------------------------------------
    # Reference texts section (below insert button)
    # ------------------------------------------------------------------

    def _build_ref_texts_section(self) -> ft.Control | None:
        """
        Build a helper section showing up to 3 physician-authored reference texts.

        Returns None (and shows nothing) when all 3 slots are empty.
        Only non-empty slots are rendered.
        Each text is shown in a read-only but selectable/copyable TextField.
        """
        texts = self._cluster.reference_texts  # always a 3-item list
        labels = ["Referenztext 1", "Referenztext 2", "Referenztext 3"]
        non_empty = [(lbl, txt) for lbl, txt in zip(labels, texts) if txt.strip()]
        if not non_empty:
            return None

        rows: list[ft.Control] = []
        for lbl, txt in non_empty:
            def _make_take(t: str):
                def _handler(e, _t=t):
                    self._guarded_raw_take(_t)
                return _handler

            def _make_append(t: str):
                def _handler(e, _t=t):
                    self._raw_append(_t)
                return _handler

            rows.append(
                ft.Column(
                    controls=[
                        ft.TextField(
                            label=lbl,
                            value=txt,
                            multiline=True,
                            min_lines=2,
                            max_lines=6,
                            read_only=True,
                            border_color=_C_BORDER,
                            bgcolor=_C_BG_MAIN,
                        ),
                        ft.Row(
                            controls=[
                                ft.OutlinedButton(
                                    "Übernehmen",
                                    icon=ft.Icons.SWAP_HORIZ,
                                    on_click=_make_take(txt),
                                    style=ft.ButtonStyle(color=_C_WARN),
                                ),
                                ft.OutlinedButton(
                                    "Anhängen",
                                    icon=ft.Icons.ADD,
                                    on_click=_make_append(txt),
                                    style=ft.ButtonStyle(color=_C_ACCENT),
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=4,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Divider(height=1, color=_C_BORDER),
                    ft.Container(height=4),
                    ft.Text(
                        "Textvorlagen",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=_C_TEXT_SECONDARY,
                    ),
                    ft.Text(
                        "Direkt übernehmen oder anhängen – "
                        "besonders nützlich für seltene Beschwerden ohne Formularfelder.",
                        size=10,
                        color=_C_TEXT_HELPER,
                        italic=True,
                    ),
                    *rows,
                ],
                spacing=8,
            ),
            padding=ft.padding.only(top=8),
        )

    def _guarded_raw_take(self, text: str, after_fn=None) -> None:
        """Replace Arbeitstext with text; confirm first if field already has content.

        after_fn: optional zero-argument callable invoked only after the text is
        actually accepted (either directly or via dialog confirmation).
        Used by _on_generate_raw to trigger the post-generation continuation row.
        NOT called when the user cancels the replace dialog.
        """
        def _do_accept() -> None:
            self._raw_take(text)
            if after_fn is not None:
                after_fn()

        if not (self._raw_field.value or "").strip():
            _do_accept()
            return

        dlg: ft.AlertDialog  # forward reference for closures

        def _do_confirm(ev) -> None:
            self._page.close(dlg)
            _do_accept()

        def _do_cancel(ev) -> None:
            self._page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Arbeitstext ersetzen?"),
            content=ft.Text("Möchten Sie den bisherigen Arbeitstext ersetzen?"),
            actions=[
                ft.TextButton("Abbrechen", on_click=_do_cancel),
                ft.TextButton("Ersetzen", on_click=_do_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.open(dlg)

    def _raw_take(self, text: str) -> None:
        """Replace RAW field with the given text block."""
        self._raw_text = text
        self._raw_field.value = text
        self._stage_labels["raw"].color = _C_OK
        self._connect_btn.disabled = False
        self._refine_btn.disabled = False
        self._insert_btn.disabled = False
        self._status_text.value = "Beschwerde übernommen."
        self._status_text.color = _C_OK
        self._page.update()

    def _raw_append(self, text: str) -> None:
        """Append the given text block to the RAW field."""
        existing = (self._raw_field.value or "").rstrip()
        self._raw_text = (existing + "\n\n" + text) if existing else text
        self._raw_field.value = self._raw_text
        self._stage_labels["raw"].color = _C_OK
        self._connect_btn.disabled = False
        self._refine_btn.disabled = False
        self._insert_btn.disabled = False
        self._status_text.value = "Beschwerde angehängt."
        self._status_text.color = _C_OK
        self._page.update()

    def _raw_prepend(self, text: str) -> None:
        """Prepend text to the very beginning of the Arbeitstext field."""
        existing = (self._raw_field.value or "").strip()
        self._raw_text = (text + "\n\n" + existing) if existing else text
        self._raw_field.value = self._raw_text
        self._stage_labels["raw"].color = _C_OK
        self._connect_btn.disabled = False
        self._refine_btn.disabled = False
        self._insert_btn.disabled = False
        self._status_text.value = "Einleitung eingefügt."
        self._status_text.color = _C_OK
        self._page.update()

    def _on_intro_insert(self, e) -> None:
        """Insert the selected intro phrase at the start of Arbeitstext.
        Both intro types (Neuer Fall, Bekannte/r Patient/in) use the phrase picker —
        phrase is always read from _intro_phrase_dd.
        """
        if not hasattr(self, "_intro_phrase_dd"):
            return
        block = (self._intro_phrase_dd.value or "").strip()
        if block:
            self._raw_prepend(block)

    # ------------------------------------------------------------------
    # Form data collection
    # ------------------------------------------------------------------

    def _collect_form_data(self) -> dict:
        result = {}
        for field_def in self._cluster.form_fields:
            fid    = field_def["id"]
            widget = self._form_widgets.get(fid)
            if widget is None:
                continue
            if isinstance(widget, set):
                result[fid] = sorted(widget)
            elif isinstance(widget, ft.Dropdown):
                val = widget.value
                result[fid] = val if val and val != "—" else None
            elif isinstance(widget, ft.TextField):
                val = (widget.value or "").strip()
                result[fid] = val if val else None
            else:
                result[fid] = None
        return result

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # State transitions: aufbau ↔ bearbeitung
    # ------------------------------------------------------------------

    def _advance_to_bearbeitung(self, e) -> None:
        """Save aufbau snapshot and switch to bearbeitung state."""
        self._snapshot_aufbau = self._raw_field.value or ""
        self._composer_state  = "bearbeitung"

        # Left panel and summary panel hidden in bearbeitung
        if self._form_panel_ctrl:
            self._form_panel_ctrl.visible = False
        if self._form_divider_ctrl:
            self._form_divider_ctrl.visible = False
        if self._summary_divider_ctrl:
            self._summary_divider_ctrl.visible = False
        if self._summary_panel_ctrl:
            self._summary_panel_ctrl.visible = False

        # aufbau-only controls → hide
        self._block_row_ctrl.visible         = False
        self._transition_row_ctrl.visible    = False
        self._weitere_row_ctrl.visible       = False
        self._continuation_row_ctrl.visible  = False
        self._connect_btn_row_ctrl.visible   = False
        self._advance_row_ctrl.visible       = False
        if self._ref_section_ctrl is not None:
            self._ref_section_ctrl.visible = False

        # bearbeitung-only controls → show
        self._back_row_ctrl.visible               = True
        self._refine_btn_row_ctrl.visible         = True
        self._advance_to_ausgabe_row_ctrl.visible = True

        # ausgabe-only controls → ensure hidden
        self._back_to_bearbeitung_row_ctrl.visible = False
        self._final_btn_row_ctrl.visible           = False
        self._insert_btn_row_ctrl.visible          = False

        # Enable refine button if there is content to work with
        self._refine_btn.disabled = not bool((self._raw_field.value or "").strip())

        self._status_text.value = "Bearbeitung aktiv."
        self._status_text.color = _C_TEXT_HELPER
        self._page.update()

    def _return_to_aufbau(self, e) -> None:
        """Confirm and return to aufbau, restoring the aufbau snapshot."""
        dlg: ft.AlertDialog  # forward reference for closures

        def _do_confirm(ev) -> None:
            self._page.close(dlg)
            self._do_return_to_aufbau()

        def _do_cancel(ev) -> None:
            self._page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Zurück zum Aufbau?"),
            content=ft.Text(
                "Die aktuelle Bearbeitung wird verworfen.\n"
                "Der Aufbaustand wird wiederhergestellt."
            ),
            actions=[
                ft.TextButton("Abbrechen", on_click=_do_cancel),
                ft.TextButton("Zurück zum Aufbau", on_click=_do_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.open(dlg)

    def _do_return_to_aufbau(self) -> None:
        """Restore aufbau snapshot and switch back to aufbau state."""
        self._raw_field.value = self._snapshot_aufbau
        self._raw_text        = self._snapshot_aufbau
        self._composer_state  = "aufbau"

        # Restore left panel and summary panel
        if self._form_panel_ctrl:
            self._form_panel_ctrl.visible = True
        if self._form_divider_ctrl:
            self._form_divider_ctrl.visible = True
        if self._summary_divider_ctrl:
            self._summary_divider_ctrl.visible = True
        if self._summary_panel_ctrl:
            self._summary_panel_ctrl.visible = True

        # aufbau-only controls → show
        self._block_row_ctrl.visible       = True
        self._transition_row_ctrl.visible  = True
        self._weitere_row_ctrl.visible     = bool(
            self._summary and (self._summary.additional_complaints or "").strip()
        )
        self._connect_btn_row_ctrl.visible = True
        self._advance_row_ctrl.visible     = True
        if self._ref_section_ctrl is not None:
            self._ref_section_ctrl.visible = True

        # bearbeitung-only controls → hide
        self._back_row_ctrl.visible               = False
        self._refine_btn_row_ctrl.visible         = False
        self._advance_to_ausgabe_row_ctrl.visible = False

        # ausgabe-only controls → hide
        self._back_to_bearbeitung_row_ctrl.visible = False
        self._final_btn_row_ctrl.visible           = False
        self._insert_btn_row_ctrl.visible          = False

        has_content = bool((self._raw_field.value or "").strip())
        self._connect_btn.disabled = not has_content
        self._insert_btn.disabled  = not has_content

        self._status_text.value = "Aufbau wiederhergestellt."
        self._status_text.color = _C_WARN
        self._page.update()

    # ------------------------------------------------------------------
    # State transitions: bearbeitung ↔ ausgabe
    # ------------------------------------------------------------------

    def _advance_to_ausgabe(self, e) -> None:
        """Save bearbeitung snapshot and switch to ausgabe state."""
        self._snapshot_bearbeitung = self._raw_field.value or ""
        self._composer_state       = "ausgabe"

        # bearbeitung-only controls → hide
        self._back_row_ctrl.visible               = False
        self._refine_btn_row_ctrl.visible         = False
        self._advance_to_ausgabe_row_ctrl.visible = False

        # ausgabe-only controls → show
        self._back_to_bearbeitung_row_ctrl.visible = True
        self._final_btn_row_ctrl.visible           = True
        self._insert_btn_row_ctrl.visible          = True

        # Enable final button if there is content
        self._final_btn.disabled  = not bool((self._raw_field.value or "").strip())
        self._insert_btn.disabled = not bool((self._raw_field.value or "").strip())

        self._status_text.value = "Ausgabe aktiv."
        self._status_text.color = _C_TEXT_HELPER
        self._page.update()

    def _return_to_bearbeitung(self, e) -> None:
        """Restore bearbeitung snapshot and switch back to bearbeitung state."""
        self._raw_field.value = self._snapshot_bearbeitung
        self._raw_text        = self._snapshot_bearbeitung
        self._composer_state  = "bearbeitung"

        # ausgabe-only controls → hide
        self._back_to_bearbeitung_row_ctrl.visible = False
        self._final_btn_row_ctrl.visible           = False
        self._insert_btn_row_ctrl.visible          = False

        # bearbeitung-only controls → show
        self._back_row_ctrl.visible               = True
        self._refine_btn_row_ctrl.visible         = True
        self._advance_to_ausgabe_row_ctrl.visible = True

        has_content = bool((self._raw_field.value or "").strip())
        self._refine_btn.disabled = not has_content

        self._status_text.value = "Bearbeitung wiederhergestellt."
        self._status_text.color = _C_WARN
        self._page.update()

    def _on_connect_blocks(self, e) -> None:
        """
        Assembly step: split current RAW content into blocks (by \\n\\n),
        send them to the LLM as an ordered list, and replace RAW with the
        linguistically connected paragraph.

        Content is closed — AI only shapes language, adds no new facts.
        """
        raw = (self._raw_field.value or "").strip()
        if not raw:
            return

        blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]

        self._status_text.value = "Verbinde …"
        self._status_text.color = _C_IN_PROGRESS
        self._connect_btn.disabled = True
        self._page.update()

        def _done(result: str) -> None:
            self._raw_text = result
            self._raw_field.value = result
            self._stage_labels["raw"].color = _C_OK
            self._connect_btn.disabled = False
            self._refine_btn.disabled = False
            self._insert_btn.disabled = False
            self._status_text.value = "Sprachlich verbunden."
            self._status_text.color = _C_OK
            self._page.update()

        def _err(msg: str) -> None:
            self._status_text.value = f"Verbindungs-Fehler: {msg}"
            self._status_text.color = _C_ERR
            self._connect_btn.disabled = False
            self._page.update()

        _svc.generate_connected(blocks, on_done=_done, on_error=_err)

    def _on_generate_raw(self, e) -> None:
        form_data = self._collect_form_data()
        try:
            raw = _svc.generate_raw(self._cluster, form_data)
        except Exception as exc:
            self._status_text.value = f"Fehler: {exc}"
            self._status_text.color = _C_ERR
            self._page.update()
            return
        if self._active_block_index > 0:
            # Block 2+: append to preserve cumulative text from earlier blocks.
            # No "replace?" dialog — cumulative content must not be destroyed.
            self._raw_append(raw)
            self._on_generation_accepted()
        else:
            # Block 1: existing guard — shows confirmation dialog when Arbeitstext
            # already has content, inserts directly when empty.
            # after_fn triggers the continuation row only after actual acceptance.
            self._guarded_raw_take(raw, after_fn=self._on_generation_accepted)

    def _on_refine(self, e) -> None:
        raw = self._raw_field.value or self._raw_text
        if not raw.strip():
            return
        self._status_text.value = "Verfeinere..."
        self._status_text.color = _C_IN_PROGRESS
        self._refine_btn.disabled = True
        self._page.update()

        def _done(result: str) -> None:
            self._refined_text = result
            self._refined_field.value = result   # internal compatibility
            self._raw_text = result              # sync backing store
            self._raw_field.value = result       # write into the single visible field
            self._insert_btn.disabled = False
            self._status_text.value = "Sprachlich geglättet."
            self._status_text.color = _C_OK
            self._refine_btn.disabled = False
            self._page.update()

        def _err(msg: str) -> None:
            self._status_text.value = f"LLM-Fehler: {msg}"
            self._status_text.color = _C_ERR
            self._refine_btn.disabled = False
            self._page.update()

        _svc.generate_refined(self._cluster, raw, on_done=_done, on_error=_err)

    def _on_finalize(self, e) -> None:
        text = self._raw_field.value or self._raw_text
        if not text.strip():
            return
        self._status_text.value = "Verdichtung läuft …"
        self._status_text.color = _C_IN_PROGRESS
        self._final_btn.disabled = True
        self._page.update()

        def _done(result: str) -> None:
            self._final_text = result
            self._final_field.value = result     # internal compatibility
            self._raw_text = result              # sync backing store
            self._raw_field.value = result       # write into the single visible field
            self._insert_btn.disabled = False
            self._status_text.value = "Verdichtet."
            self._status_text.color = _C_OK
            self._final_btn.disabled = False
            self._page.update()

        def _err(msg: str) -> None:
            self._status_text.value = f"LLM-Fehler: {msg}"
            self._status_text.color = _C_ERR
            self._final_btn.disabled = False
            self._page.update()

        _svc.generate_final(self._cluster, text, on_done=_done, on_error=_err)

    def _on_insert(self, e) -> None:
        """
        Insert the best available draft into the Aufnahme-Schablone.
        Priority: Final > Refined > Raw.
        Also appends to controller.state.composed_blocks.
        """
        text = (
            self._final_field.value
            or self._refined_field.value
            or self._raw_field.value
            or ""
        ).strip()
        if not text:
            return

        self._ctrl.state.composed_blocks.append(text)

        path = self._ctrl.state.schablone_path
        if path:
            try:
                from services.document_service import insert_blocks_into_section
                insert_blocks_into_section(path, [text])
                self._status_text.value = "Text in Schablone eingefügt."
                self._status_text.color = _C_OK
            except Exception as exc:
                self._status_text.value = f"Export-Fehler: {exc}"
                self._status_text.color = _C_ERR
        else:
            self._status_text.value = "Text gespeichert (keine Schablone geladen)."
            self._status_text.color = _C_WARN

        self._page.update()
