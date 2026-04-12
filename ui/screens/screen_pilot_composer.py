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

import flet as ft

from models.case_summary import CaseSummary
from models.unified_cluster import UnifiedCluster
from services.unified_cluster_service import load, load_lws
import services.pilot_draft_service as _svc
from services.pilot_draft_service import HAS_LLM


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
    ) -> None:
        self._page    = page
        self._ctrl    = controller
        self._summary = summary
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
          additional_notes ← priority_complaint + additional_complaints
            (the physician's interview notes make natural free-text context)

        Important: no draft is auto-generated here.
        The physician must click "Roh-Entwurf generieren" explicitly.
        """
        parts = [
            p
            for p in [summary.priority_complaint, summary.additional_complaints]
            if p and p.strip()
        ]
        note_text = " ".join(parts).strip()

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

        Two-step: category dropdown → phrase dropdown → Einfügen button.
        Inserts the selected full intro block at the BEGINNING of Arbeitstext.

        Block-level selection: one dropdown with intro type choices,
        each mapping to a predefined full text block.  No sentence-by-sentence
        composition.

        Defined blocks:
          - "Neuer Fall"            → first opener phrase from cluster.sprachbausteine
                                      (single representative opener)
          - "Bekannte/r Patient/in" → fixed full intro block (4 sentences)

        The lower Textvorlagen section remains the only place for full
        complaint/reference texts.
        """
        # --- Block definitions ---
        # "Bekannte/r Patient/in": exact full block as specified.
        _BEKANNTE_BLOCK = (
            "Patient/in ist im Hause bekannt. "
            "Zuletzt befand sich Patient/in im Jahr XXXX in unserer stationären Behandlung. "
            "Die ausführliche Vorgeschichte darf freundlicherweise als bekannt vorausgesetzt "
            "werden; wir verweisen auf die entsprechenden Vorberichte. "
            "Kurz gefasst berichtet Patient/in seit ..."
        )

        # "Neuer Fall": all opener phrases from cluster (multiple alternatives).
        _neuer_fall_phrases = self._cluster.sprachbausteine.get("Einstieg – neuer Fall", [])

        # self._intro_blocks holds entries for types that map to a single fixed block.
        # "Neuer Fall" is handled via _intro_phrase_dd and is NOT in this dict.
        self._intro_blocks: dict[str, str] = {
            "Bekannte/r Patient/in": _BEKANNTE_BLOCK,
        }

        # Build type dropdown options: Neuer Fall first (if phrases available), then bekannte.
        _type_options: list[str] = []
        if _neuer_fall_phrases:
            _type_options.append("Neuer Fall")
        _type_options.append("Bekannte/r Patient/in")

        self._intro_block_dd = ft.Dropdown(
            hint_text="Einleitungstyp wählen …",
            options=[ft.dropdown.Option(k) for k in _type_options],
            border_color=_C_BORDER,
            dense=True,
            width=240,
        )

        # Phrase dropdown — only shown when "Neuer Fall" is selected.
        self._intro_phrase_dd = ft.Dropdown(
            hint_text="Formulierung wählen …",
            options=[ft.dropdown.Option(p) for p in _neuer_fall_phrases],
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
            if selected == "Neuer Fall":
                # Show phrase picker; insert requires a phrase selection.
                self._intro_phrase_dd.visible = True
                self._intro_phrase_dd.value = None
                self._intro_insert_btn.disabled = True
            else:
                # Single fixed block — hide phrase picker, enable insert immediately.
                self._intro_phrase_dd.visible = False
                self._intro_insert_btn.disabled = not bool(selected)
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

        Single dropdown populated from cluster.sprachbausteine key
        "Anschluss / Überleitung" + Einfügen button.
        Appends the selected phrase to the END of Arbeitstext.
        """
        phrases = self._cluster.sprachbausteine.get("Anschluss / Überleitung", [])

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

    def _guarded_raw_take(self, text: str) -> None:
        """Replace Arbeitstext with text; confirm first if field already has content."""
        if not (self._raw_field.value or "").strip():
            self._raw_take(text)
            return

        dlg: ft.AlertDialog  # forward reference for closures

        def _do_confirm(ev) -> None:
            self._page.close(dlg)
            self._raw_take(text)

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
        """Insert the selected intro text at the start of Arbeitstext.
        Bekannte/r Patient/in: uses the fixed full block.
        Neuer Fall: uses the phrase selected in _intro_phrase_dd.
        """
        if not hasattr(self, "_intro_block_dd") or not self._intro_block_dd.value:
            return
        selected_type = self._intro_block_dd.value
        if selected_type in self._intro_blocks:
            # Fixed block (e.g. Bekannte/r Patient/in)
            block = self._intro_blocks[selected_type]
        else:
            # Phrase-based (e.g. Neuer Fall)
            block = (self._intro_phrase_dd.value or "").strip() if hasattr(self, "_intro_phrase_dd") else ""
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
        self._block_row_ctrl.visible       = False
        self._transition_row_ctrl.visible  = False
        self._connect_btn_row_ctrl.visible = False
        self._advance_row_ctrl.visible     = False
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
        # Route through guard: shows confirmation dialog when Arbeitstext already
        # has content, inserts directly when empty.
        self._guarded_raw_take(raw)

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
