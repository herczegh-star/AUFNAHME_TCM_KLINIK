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
from services.unified_cluster_service import load, save_edited, list_available, create_cluster, slugify_cluster_id
from services.cluster_validator import validate_cluster_dict
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
        # render_maps editor: section_key → {entries: list[dict], col: Column, container: Control}
        self._rm_sections: dict[str, dict] = {}
        self._rm_outer_col: ft.Column | None = None
        # form fields editor: list of row-state dicts; populated in _build_tab_form_fields()
        self._field_rows: list[dict] = []
        self._field_list_col: ft.Column | None = None
        # normalization editor: section_key → {pairs, col, container}
        self._norm_sections: dict[str, dict] = {}
        self._norm_outer_col: ft.Column | None = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self) -> None:
        self._page.add(
            ft.Column(
                controls=[
                    self._build_header(),
                    ft.Divider(height=1, color=_C_BORDER),
                    ft.Tabs(
                        tabs=[
                            ft.Tab(text="Meta",            content=self._build_tab_meta()),
                            ft.Tab(text="Stil-Regeln",     content=self._build_tab_style()),
                            ft.Tab(text="Archetypen",      content=self._build_tab_archetypes()),
                            ft.Tab(text="Tests",           content=self._build_tab_tests()),
                            ft.Tab(text="Render-Phrasen",  content=self._build_tab_render_maps()),
                            ft.Tab(text="Formular-Felder", content=self._build_tab_form_fields()),
                            ft.Tab(text="Normalisierung",  content=self._build_tab_normalization()),
                        ],
                        expand=True,
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
                    ft.OutlinedButton(
                        "+ Neuer Cluster",
                        on_click=self._on_new_cluster_click,
                        style=ft.ButtonStyle(
                            color=_C_ACCENT,
                            side=ft.BorderSide(1, _C_ACCENT),
                        ),
                    ),
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
                    ft.VerticalDivider(width=1, color=_C_BORDER),
                    self._status,
                    ft.ElevatedButton(
                        "Speichern",
                        icon=ft.Icons.SAVE,
                        bgcolor=_C_ACCENT,
                        color=ft.Colors.WHITE,
                        on_click=self._on_save,
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

    def _on_new_cluster_click(self, e) -> None:
        id_preview = ft.Text(
            "Cluster-ID: —",
            size=11,
            color=ft.Colors.BLUE_GREY_500,
            italic=True,
        )
        err_text = ft.Text("", color=_C_ERR, size=11)

        def _update_preview(ev) -> None:
            slug = slugify_cluster_id((tf_name.value or "").strip())
            id_preview.value = f"Cluster-ID: {slug}" if slug else "Cluster-ID: —"
            self._page.update()

        tf_name = ft.TextField(
            label="Anzeigename",
            hint_text="z. B. Schulter-Syndrom",
            border_color=_C_BORDER,
            autofocus=True,
            on_change=_update_preview,
        )

        def _close(e2) -> None:
            dlg.open = False
            self._page.update()

        def _create(e2) -> None:
            raw_name   = (tf_name.value or "").strip()
            cluster_id = slugify_cluster_id(raw_name)
            try:
                new_cluster = create_cluster(cluster_id, raw_name)
            except ValueError as exc:
                err_text.value = str(exc)
                self._page.update()
                return
            dlg.open = False
            self._page.update()
            self._ctrl.show_cluster_builder(storage_key=new_cluster.storage_key)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Neuer Cluster"),
            content=ft.Column(
                controls=[tf_name, id_preview, err_text],
                tight=True,
                spacing=8,
                width=360,
            ),
            actions=[
                ft.TextButton("Abbrechen", on_click=_close),
                ft.ElevatedButton(
                    "Erstellen",
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=_create,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

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

    def _build_tab_render_maps(self) -> ft.Control:
        """
        Editor for cluster.render_maps — dynamic sections from cluster JSON.
        Each section: editable canonical key + editable phrase value + delete.
        """
        self._rm_sections = {}
        self._rm_outer_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        for section_key, section_dict in self._cluster.render_maps.items():
            sd = self._build_rm_section(section_key, section_dict)
            self._rm_sections[section_key] = sd
            self._rm_outer_col.controls.append(sd["container"])

        add_section_btn = ft.OutlinedButton(
            "+ Neue Sektion",
            icon=ft.Icons.ADD,
            on_click=self._on_add_rm_section,
            style=ft.ButtonStyle(color=_C_ACCENT, side=ft.BorderSide(1, _C_ACCENT)),
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([add_section_btn]),
                    ft.Divider(height=1, color=_C_BORDER),
                    self._rm_outer_col,
                ],
                spacing=8,
                expand=True,
            ),
            padding=16,
            expand=True,
        )

    def _build_rm_section(self, section_key: str, section_dict: dict) -> dict:
        """Build one render_maps section block."""
        entries: list[dict] = []
        entries_col = ft.Column(spacing=4)

        for canonical, phrase in section_dict.items():
            er = self._build_rm_entry_row(canonical, phrase, section_key)
            entries.append(er)
            entries_col.controls.append(er["container"])

        add_entry_btn = ft.TextButton(
            "+ Eintrag",
            icon=ft.Icons.ADD,
            on_click=lambda e, sk=section_key: self._on_add_rm_entry(sk, e),
            style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY_600),
        )

        sd: dict = {"entries": entries, "col": entries_col, "container": None}
        sd["container"] = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Text(
                            section_key,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.BLUE_700,
                            expand=True,
                        ),
                    ]),
                    ft.Divider(height=1, color=_C_BORDER),
                    entries_col,
                    ft.Row([add_entry_btn]),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.border.all(1, _C_BORDER),
            border_radius=6,
        )
        return sd

    def _build_rm_entry_row(self, canonical: str, phrase: str, section_key: str) -> dict:
        """Build one canonical → phrase entry row."""
        tf_canonical = ft.TextField(
            value=canonical,
            label="canonical",
            border_color=_C_BORDER,
            dense=True,
            expand=True,
        )
        tf_phrase = ft.TextField(
            value=phrase,
            label="Phrase",
            border_color=_C_BORDER,
            dense=True,
            expand=True,
        )
        entry_data: dict = {
            "tf_canonical": tf_canonical,
            "tf_phrase":    tf_phrase,
            "container":    None,
        }
        del_btn = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            icon_color=_C_ERR,
            icon_size=16,
            tooltip="Eintrag entfernen",
            on_click=lambda e, sk=section_key, ed=entry_data: self._on_delete_rm_entry(sk, ed, e),
        )
        entry_data["container"] = ft.Row(
            controls=[
                tf_canonical,
                ft.Text("→", size=12, color=ft.Colors.BLUE_GREY_500, width=20),
                tf_phrase,
                del_btn,
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return entry_data

    def _on_add_rm_entry(self, section_key: str, e) -> None:
        sd = self._rm_sections[section_key]
        er = self._build_rm_entry_row("", "", section_key)
        sd["entries"].append(er)
        sd["col"].controls.append(er["container"])
        self._page.update()

    def _on_delete_rm_entry(self, section_key: str, entry_data: dict, e) -> None:
        sd = self._rm_sections[section_key]
        if entry_data in sd["entries"]:
            sd["entries"].remove(entry_data)
        if entry_data["container"] in sd["col"].controls:
            sd["col"].controls.remove(entry_data["container"])
        self._page.update()

    def _on_add_rm_section(self, e) -> None:
        tf_key   = ft.TextField(
            label="Sektions-Name",
            hint_text="z. B. pain_character",
            border_color=_C_BORDER,
            autofocus=True,
        )
        err_text = ft.Text("", color=_C_ERR, size=11)

        def _close(e2) -> None:
            dlg.open = False
            self._page.update()

        def _create(e2) -> None:
            new_key = (tf_key.value or "").strip()
            if not new_key:
                err_text.value = "Sektions-Name darf nicht leer sein."
                self._page.update()
                return
            if new_key in self._rm_sections:
                err_text.value = f"Sektion '{new_key}' existiert bereits."
                self._page.update()
                return
            sd = self._build_rm_section(new_key, {})
            self._rm_sections[new_key] = sd
            self._rm_outer_col.controls.append(sd["container"])
            dlg.open = False
            self._page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Neue Render-Maps-Sektion"),
            content=ft.Column(
                controls=[tf_key, err_text],
                tight=True,
                spacing=8,
                width=320,
            ),
            actions=[
                ft.TextButton("Abbrechen", on_click=_close),
                ft.ElevatedButton(
                    "Hinzufügen",
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=_create,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    # ------------------------------------------------------------------
    # Tab 6: Formular-Felder (editor)
    # ------------------------------------------------------------------

    _FIELD_TYPES = ["text", "textarea", "number", "select", "multi_select"]
    # Keys handled explicitly by the editor — all others preserved as-is on save
    _FIELD_KNOWN_KEYS = {
        "id", "label", "type", "options", "placeholder",
        "required", "normalization_map", "shared_items_key",
        "active_in_draft",
    }

    def _build_tab_form_fields(self) -> ft.Control:
        self._field_rows = []
        self._field_list_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        for field in self._cluster.form_fields:
            row = self._build_field_row(field)
            self._field_rows.append(row)
            self._field_list_col.controls.append(row["container"])

        add_btn = ft.OutlinedButton(
            "+ Neues Feld",
            icon=ft.Icons.ADD,
            on_click=self._on_add_field,
            style=ft.ButtonStyle(color=_C_ACCENT, side=ft.BorderSide(1, _C_ACCENT)),
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([add_btn]),
                    ft.Divider(height=1, color=_C_BORDER),
                    self._field_list_col,
                ],
                spacing=8,
                expand=True,
            ),
            padding=16,
            expand=True,
        )

    def _build_field_row(self, field: dict | None = None) -> dict:
        """
        Build one editable field row.  field=None means a new empty row.
        Returns a dict with widget refs and the rendered container.
        Extra keys not handled by the editor are preserved in '_extra'.
        """
        f = field or {}
        extra = {k: v for k, v in f.items() if k not in self._FIELD_KNOWN_KEYS}

        tf_id = ft.TextField(
            value=f.get("id", ""),
            label="id",
            border_color=_C_BORDER,
            width=160,
            dense=True,
        )
        dd_type = ft.Dropdown(
            value=f.get("type", "text") if f.get("type") in self._FIELD_TYPES else "text",
            options=[ft.dropdown.Option(t) for t in self._FIELD_TYPES],
            border_color=_C_BORDER,
            width=140,
            dense=True,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=2),
        )
        cb_required = ft.Checkbox(
            label="req.",
            value=bool(f.get("required", False)),
        )
        cb_active = ft.Checkbox(
            label="aktiv im Draft",
            value=bool(f.get("active_in_draft", False)),
        )
        tf_label = ft.TextField(
            value=f.get("label", ""),
            label="label",
            border_color=_C_BORDER,
            expand=True,
            dense=True,
        )
        tf_sik = ft.TextField(
            value=f.get("shared_items_key") or "",
            label="shared_items_key",
            hint_text="z. B. pain_character  (leer = null)",
            border_color=_C_BORDER,
            expand=True,
            dense=True,
        )
        tf_norm = ft.TextField(
            value=f.get("normalization_map") or "",
            label="normalization_map",
            hint_text="z. B. character  (leer = null)",
            border_color=_C_BORDER,
            expand=True,
            dense=True,
        )
        tf_options = ft.TextField(
            value=", ".join(f["options"]) if "options" in f else "",
            label="options",
            hint_text="kommagetrennt — für select / multi_select",
            border_color=_C_BORDER,
            expand=True,
            dense=True,
        )
        tf_placeholder = ft.TextField(
            value=f.get("placeholder", ""),
            label="placeholder",
            hint_text="für text / textarea",
            border_color=_C_BORDER,
            expand=True,
            dense=True,
        )

        row_data: dict = {
            "tf_id":          tf_id,
            "dd_type":        dd_type,
            "cb_required":    cb_required,
            "cb_active":      cb_active,
            "tf_label":       tf_label,
            "tf_sik":         tf_sik,
            "tf_norm":        tf_norm,
            "tf_options":     tf_options,
            "tf_placeholder": tf_placeholder,
            "_extra":         extra,
            "container":      None,  # filled below
        }

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=_C_ERR,
            icon_size=18,
            tooltip="Feld entfernen",
            on_click=lambda e, rd=row_data: self._on_delete_field(rd, e),
        )

        container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[tf_id, dd_type, cb_required, cb_active,
                                  ft.Container(expand=True), delete_btn],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    tf_label,
                    ft.Row(controls=[tf_sik, tf_norm], spacing=8),
                    ft.Row(controls=[tf_options, tf_placeholder], spacing=8),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.all(1, _C_BORDER),
            border_radius=6,
        )
        row_data["container"] = container
        return row_data

    def _on_add_field(self, e) -> None:
        row = self._build_field_row(None)
        self._field_rows.append(row)
        self._field_list_col.controls.append(row["container"])
        self._page.update()

    def _on_delete_field(self, row_data: dict, e) -> None:
        if row_data in self._field_rows:
            self._field_rows.remove(row_data)
        if row_data["container"] in self._field_list_col.controls:
            self._field_list_col.controls.remove(row_data["container"])
        self._page.update()

    # ------------------------------------------------------------------
    # Tab 7: Normalisierung (editor)
    # ------------------------------------------------------------------

    def _build_tab_normalization(self) -> ft.Control:
        self._norm_sections = {}
        self._norm_outer_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        for section_key, pairs_dict in self._cluster.normalization_maps.items():
            sd = self._build_norm_section(section_key, pairs_dict)
            self._norm_sections[section_key] = sd
            self._norm_outer_col.controls.append(sd["container"])

        add_section_btn = ft.OutlinedButton(
            "+ Neue Sektion",
            icon=ft.Icons.ADD,
            on_click=self._on_add_norm_section,
            style=ft.ButtonStyle(color=_C_ACCENT, side=ft.BorderSide(1, _C_ACCENT)),
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([add_section_btn]),
                    ft.Divider(height=1, color=_C_BORDER),
                    self._norm_outer_col,
                ],
                spacing=8,
                expand=True,
            ),
            padding=16,
            expand=True,
        )

    def _build_norm_section(self, section_key: str, pairs_dict: dict) -> dict:
        """Build one normalization section block with its pair rows."""
        pairs: list[dict] = []
        pairs_col = ft.Column(spacing=4)

        for alias, canonical in pairs_dict.items():
            pr = self._build_norm_pair_row(alias, canonical, section_key)
            pairs.append(pr)
            pairs_col.controls.append(pr["container"])

        add_pair_btn = ft.TextButton(
            "+ Alias",
            icon=ft.Icons.ADD,
            on_click=lambda e, sk=section_key: self._on_add_norm_pair(sk, e),
            style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY_600),
        )

        section_data: dict = {"pairs": pairs, "col": pairs_col, "container": None}

        section_data["container"] = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Text(
                            section_key,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.BLUE_700,
                            expand=True,
                        ),
                    ]),
                    ft.Divider(height=1, color=_C_BORDER),
                    pairs_col,
                    ft.Row([add_pair_btn]),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.border.all(1, _C_BORDER),
            border_radius=6,
        )
        return section_data

    def _build_norm_pair_row(self, alias: str, canonical: str, section_key: str) -> dict:
        """Build one alias → canonical pair row."""
        tf_alias = ft.TextField(
            value=alias,
            label="alias",
            border_color=_C_BORDER,
            dense=True,
            expand=True,
        )
        tf_canonical = ft.TextField(
            value=canonical,
            label="canonical",
            border_color=_C_BORDER,
            dense=True,
            expand=True,
        )
        pair_data: dict = {"tf_alias": tf_alias, "tf_canonical": tf_canonical, "container": None}

        del_btn = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            icon_color=_C_ERR,
            icon_size=16,
            tooltip="Alias entfernen",
            on_click=lambda e, sk=section_key, pd=pair_data: self._on_delete_norm_pair(sk, pd, e),
        )
        pair_data["container"] = ft.Row(
            controls=[
                tf_alias,
                ft.Text("→", size=12, color=ft.Colors.BLUE_GREY_500, width=20),
                tf_canonical,
                del_btn,
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return pair_data

    def _on_add_norm_pair(self, section_key: str, e) -> None:
        sd = self._norm_sections[section_key]
        pr = self._build_norm_pair_row("", "", section_key)
        sd["pairs"].append(pr)
        sd["col"].controls.append(pr["container"])
        self._page.update()

    def _on_delete_norm_pair(self, section_key: str, pair_data: dict, e) -> None:
        sd = self._norm_sections[section_key]
        if pair_data in sd["pairs"]:
            sd["pairs"].remove(pair_data)
        if pair_data["container"] in sd["col"].controls:
            sd["col"].controls.remove(pair_data["container"])
        self._page.update()

    def _on_add_norm_section(self, e) -> None:
        tf_key   = ft.TextField(
            label="Sektions-Name",
            hint_text="z. B. aggravating",
            border_color=_C_BORDER,
            autofocus=True,
        )
        err_text = ft.Text("", color=_C_ERR, size=11)

        def _close(e2) -> None:
            dlg.open = False
            self._page.update()

        def _create(e2) -> None:
            new_key = (tf_key.value or "").strip()
            if not new_key:
                err_text.value = "Sektions-Name darf nicht leer sein."
                self._page.update()
                return
            if new_key in self._norm_sections:
                err_text.value = f"Sektion '{new_key}' existiert bereits."
                self._page.update()
                return
            sd = self._build_norm_section(new_key, {})
            self._norm_sections[new_key] = sd
            self._norm_outer_col.controls.append(sd["container"])
            dlg.open = False
            self._page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Neue Normalisierungs-Sektion"),
            content=ft.Column(
                controls=[tf_key, err_text],
                tight=True,
                spacing=8,
                width=320,
            ),
            actions=[
                ft.TextButton("Abbrechen", on_click=_close),
                ft.ElevatedButton(
                    "Hinzufügen",
                    bgcolor=_C_ACCENT,
                    color=ft.Colors.WHITE,
                    on_click=_create,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

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

            # Apply edits from Formular-Felder tab
            # NOTE: blank-id rows are included in the dict so INV-01 can fire.
            # They are excluded from the saved list only after validation passes.
            new_fields: list[dict] = []
            for row in self._field_rows:
                fid = row["tf_id"].value.strip()
                ftype = row["dd_type"].value or "text"
                field_dict: dict = {
                    **row["_extra"],
                    "id":                fid,
                    "label":             row["tf_label"].value.strip(),
                    "type":              ftype,
                    "required":          bool(row["cb_required"].value),
                    "active_in_draft":   bool(row["cb_active"].value),
                    "normalization_map": row["tf_norm"].value.strip() or None,
                    "shared_items_key":  row["tf_sik"].value.strip() or None,
                }
                if ftype in ("select", "multi_select"):
                    raw = row["tf_options"].value or ""
                    field_dict["options"] = [o.strip() for o in raw.split(",") if o.strip()]
                placeholder = row["tf_placeholder"].value.strip()
                if placeholder:
                    field_dict["placeholder"] = placeholder
                new_fields.append(field_dict)
            d.setdefault("form", {})["fields"] = new_fields

            # Apply edits from Normalisierung tab
            new_norm: dict = {}
            for section_key, sd in self._norm_sections.items():
                section_dict: dict = {}
                for pair in sd["pairs"]:
                    alias     = pair["tf_alias"].value.strip()
                    canonical = pair["tf_canonical"].value.strip()
                    if alias and canonical:
                        section_dict[alias] = canonical
                new_norm[section_key] = section_dict  # preserve even if empty
            d["normalization"] = new_norm

            # Apply edits from Render-Phrasen tab
            new_rm: dict = {}
            for section_key, sd in self._rm_sections.items():
                section_dict: dict = {}
                for entry in sd["entries"]:
                    canonical = entry["tf_canonical"].value.strip()
                    phrase    = entry["tf_phrase"].value.strip()
                    if canonical and phrase:
                        section_dict[canonical] = phrase
                new_rm[section_key] = section_dict  # preserve even if empty
            d["render_maps"] = new_rm

            # --- Validation ---
            issues = validate_cluster_dict(d)
            errors   = [i for i in issues if i.severity == "ERROR"]
            warnings = [i for i in issues if i.severity == "WARNING"]
            infos    = [i for i in issues if i.severity == "INFO"]

            if errors:
                lines = ["Nicht gespeichert:"]
                for i in errors:
                    lines.append(f"ERROR [{i.code}] {i.message}")
                self._status.value = "  |  ".join(lines)
                self._status.color = _C_ERR
                self._page.update()
                return

            # --- Persist ---
            # Strip blank-id rows now that validation has passed (none exist
            # if errors were absent, but guard defensively).
            d["form"]["fields"] = [f for f in new_fields if f.get("id", "").strip()]

            path = save_edited(self._cluster)

            # Invalidate composer render_maps cache so PilotComposer
            # picks up the new phrases on its next load_lws() call.
            try:
                from core.ai_draft.lws_narrative_composer import _invalidate_render_maps_cache
                _invalidate_render_maps_cache()
            except Exception:
                pass  # non-critical — next app restart will reload

            if warnings or infos:
                hint_lines = [f"Gespeichert: {path.name}"]
                for i in warnings:
                    hint_lines.append(f"WARNING [{i.code}] {i.message}")
                for i in infos:
                    hint_lines.append(f"INFO [{i.code}] {i.message}")
                self._status.value = "  |  ".join(hint_lines)
                self._status.color = _C_WARN
            else:
                self._status.value = f"Gespeichert: {path.name}"
                self._status.color = _C_OK

        except Exception as exc:
            self._status.value  = f"Fehler: {exc}"
            self._status.color  = _C_ERR

        self._page.update()
