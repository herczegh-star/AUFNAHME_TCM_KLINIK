"""
screen_cluster_builder.py
--------------------------
Cluster-Editor screen — author branch of the unified cluster architecture.

Tabs:
  1. Meta          — id, name, aliases, icd10, version, status
  2. Stil-Regeln   — rules list (editable), forbidden_words
  3. Archetypen    — view/edit archetype descriptions
  4. Tests         — run embedded tests against current render_maps
  5. Formular-Vorschau — read-only preview of form field definitions

Saves to <cluster_id>.edited.json via unified_cluster_service.save_edited().
Navigation: "Zurueck" → AppController.show_pilot_composer()
"""

from __future__ import annotations

import json

import flet as ft

from models.unified_cluster import UnifiedCluster
from services.unified_cluster_service import load, save_edited, list_available
import services.pilot_draft_service as _svc


_C_BORDER   = ft.Colors.BLUE_GREY_200
_C_ACCENT   = ft.Colors.INDIGO_700
_C_OK       = ft.Colors.GREEN_700
_C_ERR      = ft.Colors.RED_700
_C_WARN     = ft.Colors.ORANGE_700
_C_BG       = ft.Colors.GREY_50


class ScreenClusterBuilder:

    def __init__(self, page: ft.Page, controller, storage_key: str | None = None) -> None:
        self._page = page
        self._ctrl = controller
        available = list_available()
        key = storage_key if (storage_key and storage_key in available) else (available[0] if available else "lws_syndrom_v1_1")
        self._cluster: UnifiedCluster = load(key)
        self._status = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_500)
        # render_maps editor: {section_name: {key: TextField}}
        self._render_map_fields: dict[str, dict[str, ft.TextField]] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self) -> None:
        self._page.add(
            ft.Column(
                controls=[
                    self._build_header(),
                    ft.Divider(height=1, color=_C_BORDER),
                    ft.Container(
                        content=ft.Tabs(
                            tabs=[
                                ft.Tab(text="Meta",             content=self._build_tab_meta()),
                                ft.Tab(text="Stil-Regeln",      content=self._build_tab_style()),
                                ft.Tab(text="Archetypen",       content=self._build_tab_archetypes()),
                                ft.Tab(text="Tests",            content=self._build_tab_tests()),
                                ft.Tab(text="Render-Phrasen",   content=self._build_tab_render_maps()),
                                ft.Tab(text="Formular-Vorschau", content=self._build_tab_form_preview()),
                            ],
                            expand=True,
                        ),
                        expand=True,
                        padding=ft.padding.only(top=8),
                    ),
                    ft.Divider(height=1, color=_C_BORDER),
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                self._status,
                                ft.Container(expand=True),
                                ft.ElevatedButton(
                                    "Speichern (.edited.json)",
                                    icon=ft.Icons.SAVE,
                                    bgcolor=_C_ACCENT,
                                    color=ft.Colors.WHITE,
                                    on_click=self._on_save,
                                ),
                            ],
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    ),
                ],
                expand=True,
                spacing=0,
            )
        )

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self) -> ft.Control:
        available = list_available()
        cluster_dropdown = ft.Dropdown(
            value=self._cluster.storage_key,
            options=[ft.dropdown.Option(key=k, text=k) for k in available],
            on_change=self._on_cluster_change,
            width=260,
            dense=True,
            border_color=_C_BORDER,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.TextButton(
                        "← Zurueck",
                        on_click=lambda _: self._ctrl.show_pilot_composer(),
                    ),
                    ft.Text("Cluster:", size=13, color=ft.Colors.BLUE_GREY_600),
                    cluster_dropdown,
                    ft.Container(expand=True),
                    ft.Text(
                        f"Cluster-Editor: {self._cluster.name}  v{self._cluster.version}",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(expand=True),
                    ft.Text(
                        f"Status: {self._cluster.status}",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )

    def _on_cluster_change(self, e) -> None:
        selected_key = e.control.value
        if selected_key and selected_key != self._cluster.storage_key:
            self._ctrl.show_cluster_builder(storage_key=selected_key)

    # ------------------------------------------------------------------
    # Tab 1: Meta
    # ------------------------------------------------------------------

    def _build_tab_meta(self) -> ft.Control:
        d = self._cluster.to_dict()
        meta = d.get("meta", {})

        self._tf_name    = ft.TextField(label="Name",    value=d.get("name", ""),           border_color=_C_BORDER)
        self._tf_icd10   = ft.TextField(label="ICD-10",  value=meta.get("icd10", ""),        border_color=_C_BORDER, width=120)
        self._tf_version = ft.TextField(label="Version", value=d.get("version", ""),         border_color=_C_BORDER, width=80)
        self._tf_status  = ft.TextField(label="Status",  value=d.get("status", ""),          border_color=_C_BORDER, width=120)
        self._tf_aliases = ft.TextField(
            label="Aliases (kommagetrennt)",
            value=", ".join(d.get("aliases", [])),
            border_color=_C_BORDER,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    self._tf_name,
                    ft.Row([self._tf_icd10, self._tf_version, self._tf_status], spacing=12),
                    self._tf_aliases,
                ],
                spacing=12,
            ),
            padding=16,
        )

    # ------------------------------------------------------------------
    # Tab 2: Stil-Regeln
    # ------------------------------------------------------------------

    def _build_tab_style(self) -> ft.Control:
        rules = self._cluster.rules
        forbidden = self._cluster.forbidden_words

        self._tf_rules = ft.TextField(
            label="Stil-Regeln (eine pro Zeile)",
            value="\n".join(rules),
            multiline=True,
            min_lines=10,
            max_lines=16,
            border_color=_C_BORDER,
        )
        self._tf_forbidden = ft.TextField(
            label="Verbotene Woerter (kommagetrennt)",
            value=", ".join(forbidden),
            border_color=_C_BORDER,
        )

        return ft.Container(
            content=ft.Column(
                controls=[self._tf_rules, self._tf_forbidden],
                spacing=12,
            ),
            padding=16,
        )

    # ------------------------------------------------------------------
    # Tab 3: Archetypen
    # ------------------------------------------------------------------

    def _build_tab_archetypes(self) -> ft.Control:
        archetypes = self._cluster.archetypes
        rows: list[ft.Control] = []

        for arch in archetypes:
            rows.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{arch['id']} — {arch['label']}", weight=ft.FontWeight.W_600),
                        ft.Text(arch.get("description", ""), size=12, color=ft.Colors.BLUE_GREY_700),
                        ft.Text(f"Anwendung: {arch.get('when_to_use', '')}", size=11, italic=True, color=ft.Colors.BLUE_GREY_500),
                        ft.Text(f"Template: {arch.get('template', '')}", size=11, color=ft.Colors.BLUE_700),
                        ft.Text(f"TCM-Muster: {', '.join(arch.get('tcm_patterns', []))}", size=11, color=ft.Colors.TEAL_700),
                    ], spacing=4),
                    padding=12,
                    border=ft.border.all(1, _C_BORDER),
                    border_radius=6,
                )
            )

        return ft.Container(
            content=ft.Column(controls=rows, spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=16,
            expand=True,
        )

    # ------------------------------------------------------------------
    # Tab 4: Tests
    # ------------------------------------------------------------------

    def _build_tab_tests(self) -> ft.Control:
        self._test_results_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

        run_btn = ft.ElevatedButton(
            "Alle Tests ausfuehren",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=_C_ACCENT,
            color=ft.Colors.WHITE,
            on_click=self._on_run_tests,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([run_btn]),
                    ft.Container(height=8),
                    self._test_results_col,
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=16,
            expand=True,
        )

    def _on_run_tests(self, e) -> None:
        self._test_results_col.controls.clear()
        tests = self._cluster.tests
        passed = 0
        failed = 0

        for test in tests:
            test_id   = test.get("id", "?")
            desc      = test.get("description", "")
            inp       = test.get("input", {})
            must_have = test.get("expected_contains", [])
            must_not  = test.get("expected_not_contains", [])

            try:
                result = _svc.generate_raw_from_shared_items(self._cluster, inp)
                ok_have  = [t for t in must_have if t not in result]
                ok_not   = [t for t in must_not  if t     in result]
                success  = not ok_have and not ok_not

                if success:
                    passed += 1
                    icon   = ft.Icons.CHECK_CIRCLE
                    color  = _C_OK
                    detail = ""
                else:
                    failed += 1
                    icon  = ft.Icons.CANCEL
                    color = _C_ERR
                    parts = []
                    if ok_have:
                        parts.append(f"Fehlt: {ok_have}")
                    if ok_not:
                        parts.append(f"Verboten vorhanden: {ok_not}")
                    detail = "  ".join(parts)

                self._test_results_col.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(icon, color=color, size=16),
                                ft.Text(f"{test_id}: {desc}", size=12, weight=ft.FontWeight.W_500),
                            ], spacing=6),
                            ft.Text(f"Output: {result}", size=11, color=ft.Colors.BLUE_GREY_600),
                            ft.Text(detail, size=11, color=color) if detail else ft.Container(),
                        ], spacing=2),
                        padding=8,
                        border=ft.border.all(1, _C_BORDER),
                        border_radius=4,
                    )
                )
            except Exception as exc:
                failed += 1
                self._test_results_col.controls.append(
                    ft.Text(f"EXCEPTION {test_id}: {exc}", color=_C_ERR, size=12)
                )

        summary_color = _C_OK if failed == 0 else _C_ERR
        self._test_results_col.controls.insert(
            0,
            ft.Text(
                f"Ergebnis: {passed}/{passed + failed} bestanden",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=summary_color,
            )
        )
        self._page.update()

    # ------------------------------------------------------------------
    # Tab 5: Render-Phrasen
    # ------------------------------------------------------------------

    # Human-readable section labels for the UI
    _RENDER_SECTION_LABELS: dict[str, str] = {
        "character_adjective":   "Schmerzcharakter-Adjektive  (canonical → Adjektiv)",
        "radiation_phrase":      "Ausstrahlung-Phrasen  (canonical → vollständige Phrase)",
        "aggravating_dative":    "Verstärkende Faktoren  (canonical → Dativobjekt nach \"verstärkt bei\")",
        "relieving_noun":        "Lindernde Faktoren  (canonical → Substantiv nach \"gebessert durch\")",
        "temporality_adjective": "Temporalität-Adjektive  (canonical → Adjektiv)",
        "functional_phrase":     "Funktionelle Einschränkungen  (canonical → Satzfragment)",
    }

    def _build_tab_render_maps(self) -> ft.Control:
        """
        Editor for cluster.render_maps — each section rendered as a block
        of key (read-only label) + value (editable TextField) rows.
        """
        render_maps = self._cluster.render_maps
        sections: list[ft.Control] = []

        for section_key, label in self._RENDER_SECTION_LABELS.items():
            section_data = render_maps.get(section_key, {})
            self._render_map_fields[section_key] = {}

            rows: list[ft.Control] = []
            for canonical, phrase in section_data.items():
                tf = ft.TextField(
                    value=phrase,
                    border_color=_C_BORDER,
                    dense=True,
                    expand=True,
                )
                self._render_map_fields[section_key][canonical] = tf
                rows.append(
                    ft.Row(
                        controls=[
                            ft.Text(
                                canonical,
                                size=11,
                                width=220,
                                color=ft.Colors.BLUE_700,
                                weight=ft.FontWeight.W_500,
                            ),
                            tf,
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )

            sections.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                label,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Divider(height=1, color=_C_BORDER),
                            *rows,
                        ],
                        spacing=6,
                    ),
                    padding=ft.padding.only(bottom=20),
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=ft.Colors.BLUE_GREY_400),
                            ft.Text(
                                "Nur Phrasen-Werte editieren. Canonical-Keys sind fix.",
                                size=11,
                                color=ft.Colors.BLUE_GREY_400,
                                italic=True,
                            ),
                        ], spacing=6),
                    ),
                    ft.Container(height=8),
                    *sections,
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=16,
            expand=True,
        )

    # ------------------------------------------------------------------
    # Tab 6: Formular-Vorschau
    # ------------------------------------------------------------------

    def _build_tab_form_preview(self) -> ft.Control:
        rows: list[ft.Control] = []
        for f in self._cluster.form_fields:
            rows.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f["id"], size=11, width=180, color=ft.Colors.BLUE_700, weight=ft.FontWeight.W_600),
                        ft.Text(f["label"], size=12, width=200),
                        ft.Text(f["type"], size=11, width=100, color=ft.Colors.BLUE_GREY_500),
                        ft.Text("*" if f.get("required") else "", size=11, color=_C_ERR, width=20),
                        ft.Text(
                            ", ".join(f["options"]) if "options" in f else f.get("placeholder", ""),
                            size=11,
                            color=ft.Colors.BLUE_GREY_400,
                            expand=True,
                        ),
                    ], spacing=4),
                    padding=ft.padding.symmetric(vertical=4, horizontal=8),
                    border=ft.border.all(1, _C_BORDER),
                    border_radius=4,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Text("id",         size=11, width=180, weight=ft.FontWeight.BOLD),
                        ft.Text("label",      size=11, width=200, weight=ft.FontWeight.BOLD),
                        ft.Text("type",       size=11, width=100, weight=ft.FontWeight.BOLD),
                        ft.Text("req",        size=11, width=20,  weight=ft.FontWeight.BOLD),
                        ft.Text("options/placeholder", size=11,   weight=ft.FontWeight.BOLD),
                    ], spacing=4),
                    ft.Divider(height=1, color=_C_BORDER),
                    *rows,
                ],
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=16,
            expand=True,
        )

    # ------------------------------------------------------------------
    # Save handler
    # ------------------------------------------------------------------

    def _on_save(self, e) -> None:
        try:
            d = self._cluster.to_dict()

            # Apply edits from Meta tab
            d["name"]    = self._tf_name.value.strip()
            d["version"] = self._tf_version.value.strip()
            d["status"]  = self._tf_status.value.strip()
            d["aliases"] = [a.strip() for a in self._tf_aliases.value.split(",") if a.strip()]
            d.setdefault("meta", {})["icd10"] = self._tf_icd10.value.strip()

            # Apply edits from Style tab
            d["style"]["rules"] = [
                r.strip() for r in self._tf_rules.value.splitlines() if r.strip()
            ]
            d["style"]["forbidden_words"] = [
                w.strip() for w in self._tf_forbidden.value.split(",") if w.strip()
            ]

            # Apply edits from Render-Phrasen tab
            d.setdefault("render_maps", {})
            for section_key, field_map in self._render_map_fields.items():
                d["render_maps"][section_key] = {
                    canonical: tf.value.strip()
                    for canonical, tf in field_map.items()
                    if tf.value and tf.value.strip()
                }

            path = save_edited(self._cluster)

            # Invalidate composer render_maps cache so PilotComposer
            # picks up the new phrases on its next load_lws() call.
            try:
                from core.ai_draft.lws_narrative_composer import _invalidate_render_maps_cache
                _invalidate_render_maps_cache()
            except Exception:
                pass  # non-critical — next app restart will reload

            self._status.value  = f"Gespeichert: {path.name}"
            self._status.color  = _C_OK
        except Exception as exc:
            self._status.value  = f"Fehler: {exc}"
            self._status.color  = _C_ERR

        self._page.update()
