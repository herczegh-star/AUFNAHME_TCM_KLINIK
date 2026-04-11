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
# Colour palette — consistent across production screens
# ---------------------------------------------------------------------------
_C_BORDER   = ft.Colors.BLUE_GREY_200
_C_ACCENT   = ft.Colors.BLUE_700
_C_WARN     = ft.Colors.ORANGE_700
_C_OK       = ft.Colors.GREEN_700
_C_ERR      = ft.Colors.RED_700
_C_BG_PANEL = ft.Colors.BLUE_GREY_50


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

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self) -> None:
        form_panel  = self._build_form_panel()
        draft_panel = self._build_draft_panel()

        row_controls: list[ft.Control] = [
            form_panel,
            ft.VerticalDivider(width=1, color=_C_BORDER),
            draft_panel,
        ]

        if self._summary:
            from ui.components.summary_panel import SummaryPanel
            row_controls.extend([
                ft.VerticalDivider(width=1, color=_C_BORDER),
                SummaryPanel(self._summary).build(),
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

    # ------------------------------------------------------------------
    # Header row
    # ------------------------------------------------------------------

    def _build_header(self) -> ft.Control:
        if self._summary is not None:
            back_fn = lambda _: self._ctrl.show_screen_2b(self._summary)
        else:
            back_fn = lambda _: self._ctrl.show_screen_1()

        back_btn = ft.TextButton("← Zurück", on_click=back_fn)
        title = ft.Text(
            f"Pilot-Composer: {self._cluster.name}",
            size=20,
            weight=ft.FontWeight.BOLD,
        )
        builder_btn = ft.OutlinedButton(
            "Cluster-Editor →",
            on_click=lambda _: self._ctrl.show_cluster_builder(
                storage_key=self._cluster.storage_key
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
    # Left panel: form
    # ------------------------------------------------------------------

    def _build_form_panel(self) -> ft.Control:
        fields_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        for field_def in self._cluster.form_fields:
            widget = self._build_field_widget(field_def)
            if widget is not None:
                label = ft.Text(
                    field_def["label"], size=12, color=ft.Colors.BLUE_GREY_700
                )
                fields_col.controls.append(
                    ft.Column([label, widget], spacing=4, tight=True)
                )

        # Prefill from CaseSummary — only after all widgets are created
        if self._summary is not None:
            self._prefill_from_summary(self._summary)

        generate_btn = ft.ElevatedButton(
            "Roh-Entwurf generieren",
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
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=13, color=ft.Colors.BLUE_GREY_400),
                    ft.Text(
                        f"Noch nicht im Draft: {', '.join(_inactive_fields)}",
                        size=10,
                        color=ft.Colors.BLUE_GREY_400,
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
    # Right panel: 3-stage draft
    # ------------------------------------------------------------------

    def _build_draft_panel(self) -> ft.Control:
        self._stage_labels = {
            "raw":     ft.Text("1. Roh-Entwurf",      size=13, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_400),
            "refined": ft.Text("2. Verfeinerung",      size=13, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_400),
            "final":   ft.Text("3. Final-Verdichtung", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_400),
        }

        self._raw_field = ft.TextField(
            label="Roh-Entwurf",
            multiline=True, min_lines=3, max_lines=6,
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
        self._status_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_500)

        _refine_label = (
            "Verfeinern (LLM)" if HAS_LLM
            else "Verfeinern (kein LLM konfiguriert)"
        )
        _final_label = (
            "Final verdichten (LLM)" if HAS_LLM
            else "Final verdichten (kein LLM konfiguriert)"
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
                        "Stufen 2 und 3 sind ohne LLM-Konfiguration nicht aktiv. "
                        "Die Ausgabe entspricht dem Roh-Entwurf.",
                        size=11,
                        color=_C_WARN,
                    ),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            bgcolor=ft.Colors.ORANGE_50,
            border_radius=4,
            visible=not HAS_LLM,
        )

        ref_section = self._build_ref_texts_section()

        draft_controls: list[ft.Control] = [
            ft.Row([
                self._stage_labels["raw"],
                ft.Container(width=16),
                self._stage_labels["refined"],
                ft.Container(width=16),
                self._stage_labels["final"],
            ]),
            no_llm_banner,
            ft.Container(height=4),
            self._raw_field,
            ft.Row([self._refine_btn], alignment=ft.MainAxisAlignment.END),
            self._refined_field,
            ft.Row([self._final_btn], alignment=ft.MainAxisAlignment.END),
            self._final_field,
            ft.Container(height=8),
            self._status_text,
            ft.Row([self._insert_btn], alignment=ft.MainAxisAlignment.END),
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
                    self._ref_take(_t)
                return _handler

            def _make_append(t: str):
                def _handler(e, _t=t):
                    self._ref_append(_t)
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
                            bgcolor=ft.Colors.GREY_50,
                        ),
                        ft.Row(
                            controls=[
                                ft.OutlinedButton(
                                    "Übernehmen",
                                    icon=ft.Icons.SWAP_HORIZ,
                                    on_click=_make_take(txt),
                                ),
                                ft.OutlinedButton(
                                    "Anhängen",
                                    icon=ft.Icons.ADD,
                                    on_click=_make_append(txt),
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
                        "Referenztexte",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                    *rows,
                ],
                spacing=8,
            ),
            padding=ft.padding.only(top=8),
        )

    def _ref_take(self, text: str) -> None:
        """Replace RAW field with the given reference text."""
        self._raw_text = text
        self._raw_field.value = text
        self._stage_labels["raw"].color = _C_OK
        self._refine_btn.disabled = False
        self._insert_btn.disabled = False
        self._status_text.value = "Referenztext als Roh-Entwurf übernommen."
        self._status_text.color = _C_OK
        self._page.update()

    def _ref_append(self, text: str) -> None:
        """Append the given reference text to the RAW field."""
        existing = (self._raw_field.value or "").rstrip()
        self._raw_text = (existing + "\n\n" + text) if existing else text
        self._raw_field.value = self._raw_text
        self._stage_labels["raw"].color = _C_OK
        self._refine_btn.disabled = False
        self._insert_btn.disabled = False
        self._status_text.value = "Referenztext an Roh-Entwurf angehängt."
        self._status_text.color = _C_OK
        self._page.update()

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

    def _on_generate_raw(self, e) -> None:
        form_data = self._collect_form_data()
        try:
            raw = _svc.generate_raw(self._cluster, form_data)
            self._raw_text = raw
            self._raw_field.value = raw
            self._stage_labels["raw"].color = _C_OK
            self._refine_btn.disabled = False
            self._insert_btn.disabled = False
            self._status_text.value = "Roh-Entwurf bereit."
            self._status_text.color = _C_OK
        except Exception as exc:
            self._status_text.value = f"Fehler: {exc}"
            self._status_text.color = _C_ERR
        self._page.update()

    def _on_refine(self, e) -> None:
        raw = self._raw_field.value or self._raw_text
        if not raw.strip():
            return
        self._status_text.value = "Verfeinere..."
        self._status_text.color = ft.Colors.BLUE_700
        self._refine_btn.disabled = True
        self._page.update()

        def _done(result: str) -> None:
            self._refined_text = result
            self._refined_field.value = result
            self._stage_labels["refined"].color = _C_OK
            self._final_btn.disabled = False
            self._insert_btn.disabled = False
            self._status_text.value = "Verfeinerung abgeschlossen."
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
        text = self._refined_field.value or self._raw_field.value or self._raw_text
        if not text.strip():
            return
        self._status_text.value = "Final-Verdichtung läuft..."
        self._status_text.color = ft.Colors.BLUE_700
        self._final_btn.disabled = True
        self._page.update()

        def _done(result: str) -> None:
            self._final_text = result
            self._final_field.value = result
            self._stage_labels["final"].color = _C_OK
            self._insert_btn.disabled = False
            self._status_text.value = "Final-Entwurf bereit."
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
