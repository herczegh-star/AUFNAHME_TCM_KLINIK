"""
screen_composer.py
------------------
Composer screen — the main working screen for building clinical text.

Moved verbatim from ui/app.py as part of Phase 2 refactor.
No logic changes. No UI changes. Pure structural move.
"""

import flet as ft

from core.template_repository import Cluster
from core.symptom_composer import compose_symptom_text
from core.language_refiner import refine_clinical_german
from core.template_matcher import TemplateMatcher
from core.language_refiner import OpenAIRefinerClient
from core.template_repository import TemplateRepository
from models.case_summary import CaseSummary
from ui.components.summary_panel import SummaryPanel
from services.document_service import insert_blocks_into_section
from core.draft_schema import SymptomDraftInput
from core.prompt_builder import PromptBuilder
from services.style_library_service import StyleLibraryService
from services.ai_draft_service import AIDraftService


SYMPTOM_GROUPS = [
    # structured clusters
    "LWS-Syndrom",
    "HWS-Syndrom",
    "WS-Syndrom",
    "Fibromyalgie / Ganzkörperschmerzen",
    "Kopfschmerzen",
    "Migräne",
    "Reizdarm / funktionelle Verdauungsbeschwerden",
    "CED / IBD",
    "Tinnitus aurium",
    # variant clusters
    "Müdigkeit",
    # template clusters
    "Polyneuropathie",
    "Restless-Legs-Syndrom",
    "Sjögren / Sicca-Symptomatik",
    "Endometriose",
    "Interstitielle Zystitis",
    "Axiale Spondyloarthritis / Morbus Bechterew",
    "Gelenksarthrose mechanisch",
    "Trigeminusneuralgie",
    "CRPS",
]

SLOT_TO_FIELD: dict[str, tuple[str, str]] = {
    "dauer":                            ("Dauer",                           "dauer"),
    "schmerzcharakter":                 ("Schmerzcharakter",                 "charakter"),
    "charakter":                        ("Charakter",                        "charakter"),
    "ausstrahlung":                     ("Ausstrahlung",                     "ausstrahlung"),
    "lokalisation":                     ("Lokalisation / Seite",             "seite"),
    "lokalisation_und_schmerzschwerpunkt": ("Lokalisation / Schmerzschwerpunkt", "seite"),
    "verlauf":                          ("Verlauf",                          "verlauf"),
    "beginn":                           ("Beginn",                           "verlauf"),
    "beginn_und_verlauf":               ("Beginn und Verlauf",               "verlauf"),
    "verlauf_und_intensitaet":          ("Verlauf / Intensität",             "verlauf"),
    "beginn_und_entwicklung":           ("Beginn und Entwicklung",           "verlauf"),
    "diagnose_und_erkrankungsbeginn":   ("Diagnose / Erkrankungsbeginn",     "verlauf"),
    "frequenz":                         ("Frequenz / Attacken",              "verlauf"),
    "intensitaet":                      ("Intensität",                       "verlauf"),
    "aura":                             ("Aura",                             "charakter"),
    "verschlimmerungsfaktoren":         ("Verschlechterung",                 "verschlechterung"),
    "nahrungsmittelunvertraeglichkeiten": ("Nahrungsmittelunverträglichkeiten", "verschlechterung"),
    "linderungsfaktoren":               ("Linderung",                        "linderung"),
    "therapie":                         ("Therapie / Linderung",             "linderung"),
    "begleitsymptome":                  ("Begleitsymptome",                  "begleitsymptome"),
    "funktionelle_einschraenkung":      ("Funktionelle Einschränkung",       "begleitsymptome"),
    "funktionelle_folgen":              ("Funktionelle Folgen",              "begleitsymptome"),
    "therapieverlauf":                  ("Therapieverlauf",                  "begleitsymptome"),
    "vorbefunde_und_diagnostik":        ("Vorbefunde / Diagnostik",          "begleitsymptome"),
    "diagnostik":                       ("Diagnostik / Vorbefunde",          "begleitsymptome"),
    "stuhlfrequenz_und_konsistenz":     ("Stuhlfrequenz / Konsistenz",       "charakter"),
    "bauchschmerzen":                   ("Bauchschmerzen",                   "ausstrahlung"),
    "weitere_gastrointestinale_symptome": ("Weitere GI-Symptome",           "begleitsymptome"),
    "weitere_symptome":                 ("Weitere Symptome",                 "begleitsymptome"),
    "extraintestinale_manifestationen": ("Extraintestinale Manifestationen", "begleitsymptome"),
    "befallsmuster":                    ("Befallsmuster",                    "ausstrahlung"),
    "operationen":                      ("Operationen / Eingriffe",          "begleitsymptome"),
}

DEFAULT_FIELD_DEFS: list[tuple[str, str, str]] = [
    ("Dauer",           "dauer",            "z.B. seit 5 Jahren"),
    ("Verlauf",         "verlauf",          "z.B. progredient, fluktuierend"),
    ("Charakter",       "charakter",        "z.B. stechend, brennend"),
    ("Verschlechterung","verschlechterung", "z.B. Stress, Belastung"),
    ("Linderung",       "linderung",        "z.B. Wärme, Ruhe"),
    ("Begleitsymptome", "begleitsymptome",  "z.B. Übelkeit, Kribbeln"),
]


_CLUSTER_HINTS: dict[str, dict[str, str]] = {
    "LWS-Syndrom": {
        "pain_quality":        "dumpf-drückend, ziehend, stechend, …",
        "radiation":           "ins Gesäß, Oberschenkel, Bein, …",
        "aggravating":         "langes Sitzen, Heben, Kälte, Stress, …",
        "relieving":           "Wärme, Entlastungslagerung, Massage, …",
        "func_limitations":    "Sitztoleranz, Gehstrecke, Heben, …",
    },
    "HWS-Syndrom": {
        "pain_quality":        "ziehend, drückend, verspannt, brennend, …",
        "radiation":           "in Schulter, Arm, Hand, Hinterkopf, …",
        "aggravating":         "Bildschirmarbeit, Zugluft, Stress, Kopfrotation, …",
        "relieving":           "Wärme, Entlastung, Physiotherapie, …",
        "func_limitations":    "Kopfrotation, Lesen, Bildschirmarbeit, Autofahren, …",
    },
}

_DEFAULT_HINTS: dict[str, str] = {
    "pain_quality":     "ziehend, stechend, brennend, …",
    "radiation":        "z.B. in Extremitäten, Kopf, …",
    "aggravating":      "Kälte, Belastung, Stress, …",
    "relieving":        "Wärme, Ruhe, Massage, …",
    "func_limitations": "Alltag, Beruf, Freizeit, …",
}


class ScreenComposer:
    """
    Composer screen.
    Receives page and pipeline from AppController — builds nothing itself.
    """

    def __init__(
        self,
        page: ft.Page,
        pipeline: tuple[TemplateMatcher, OpenAIRefinerClient | None, TemplateRepository],
        summary: CaseSummary | None = None,
        controller=None,
    ) -> None:
        self._page = page
        self._matcher, self._llm, self._repo = pipeline
        self._summary = summary
        self._controller = controller

    def render(self) -> None:
        page       = self._page
        matcher    = self._matcher
        llm        = self._llm
        repo       = self._repo
        controller = self._controller

        # --- State ---
        active_fields: dict[str, ft.TextField] = {}
        fields_container = ft.Column(spacing=8)
        result_column    = ft.Column(spacing=16)
        blocks_column    = ft.Column(spacing=8)
        export_status    = ft.Text("", size=12)

        # --- Block list helpers ---
        def refresh_blocks_column() -> None:
            blocks = controller.state.composed_blocks if controller else []
            blocks_column.controls = [
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(b, size=12, selectable=True),
                                ft.TextButton(
                                    "Entfernen",
                                    on_click=make_remove_handler(b),
                                ),
                            ],
                        ),
                    )
                )
                for b in blocks
            ]
            blocks_column.update()
            page.update()

        def make_remove_handler(text: str):
            def on_remove(e: ft.ControlEvent) -> None:
                if controller and text in controller.state.composed_blocks:
                    controller.state.composed_blocks.remove(text)
                refresh_blocks_column()
            return on_remove

        # --- Field builder ---
        def rebuild_fields(cluster: Cluster | None) -> None:
            active_fields.clear()
            field_defs: list[tuple[str, str, str]] = []

            if cluster and cluster.mode == "structured" and cluster.struktur:
                seen_keys: set[str] = set()
                for slot in cluster.struktur:
                    if slot not in SLOT_TO_FIELD:
                        continue
                    label, form_key = SLOT_TO_FIELD[slot]
                    if form_key in seen_keys:
                        continue
                    seen_keys.add(form_key)
                    options = cluster.slot_options.get(slot, [])
                    hint = ", ".join(options[:3]) if options else ""
                    field_defs.append((label, form_key, hint))
            else:
                field_defs = DEFAULT_FIELD_DEFS

            for label, form_key, hint in field_defs:
                tf = ft.TextField(label=label, hint_text=hint, expand=True)
                active_fields[form_key] = tf

            rows: list[ft.Control] = []
            items = list(active_fields.values())
            for i in range(0, len(items), 2):
                pair = items[i : i + 2]
                rows.append(ft.Row(controls=pair, spacing=12))

            fields_container.controls = rows
            page.update()

        # --- Event handlers ---
        def on_symptom_group_change(e: ft.ControlEvent) -> None:
            group = symptom_group.value or ""
            clusters = repo.get_templates_by_section(group)
            cluster = clusters[0] if clusters else None
            rebuild_fields(cluster)
            result_column.controls.clear()
            page.update()

        def on_generate(e: ft.ControlEvent) -> None:
            group = symptom_group.value or ""
            form_data = {key: tf.value.strip() for key, tf in active_fields.items()}

            query = " ".join(filter(None, [
                group,
                form_data.get("dauer", ""),
                form_data.get("charakter", ""),
                form_data.get("verlauf", ""),
            ]))

            templates = matcher.find_best_templates(query, top_k=3)
            result_column.controls.clear()

            for i, t in enumerate(templates, 1):
                composed = compose_symptom_text(t.text, form_data, group)
                filled_text = refine_clinical_german(composed, llm_client=llm)

                def make_copy_handler(text: str):
                    def on_copy(e: ft.ControlEvent) -> None:
                        page.set_clipboard(text)
                    return on_copy

                def make_uebernehmen_handler(text: str):
                    def on_uebernehmen(e: ft.ControlEvent) -> None:
                        if controller:
                            controller.state.composed_blocks.append(text)
                            refresh_blocks_column()
                    return on_uebernehmen

                result_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text(f"{i}. {t.title}", weight=ft.FontWeight.BOLD, size=14),
                                    ft.Text(t.section, color=ft.Colors.GREY_600, size=12),
                                    ft.Divider(height=1),
                                    ft.Text(filled_text, size=13, selectable=True),
                                    ft.Row(controls=[
                                        ft.ElevatedButton("Kopieren", on_click=make_copy_handler(filled_text)),
                                        ft.ElevatedButton("Übernehmen", on_click=make_uebernehmen_handler(filled_text)),
                                    ], spacing=8),
                                ],
                            ),
                        )
                    )
                )

            page.update()

        # --- Widgets ---
        symptom_group = ft.Dropdown(
            label="Symptomgruppe",
            options=[ft.dropdown.Option(g) for g in SYMPTOM_GROUPS],
            expand=True,
            on_change=on_symptom_group_change,
        )

        rebuild_fields(None)

        # --- AI draft service ---
        _ai_svc = StyleLibraryService()
        _ai_service = AIDraftService(_ai_svc, PromptBuilder())

        # --- AI draft form fields ---
        _cluster_names = _ai_svc.get_cluster_names()
        _cluster_default = _cluster_names[0] if _cluster_names else "LWS-Syndrom"
        ai_cluster = ft.Dropdown(
            label="Cluster",
            value=_cluster_default,
            options=[ft.dropdown.Option(n) for n in _cluster_names],
            expand=True,
        )
        ai_duration     = ft.TextField(label="Dauer",           hint_text="z.B. 5 Jahre",          expand=True)
        ai_pain_quality = ft.TextField(label="Schmerzcharakter",hint_text="ziehend, stechend, …",  expand=True)
        ai_radiation    = ft.TextField(label="Ausstrahlung",    hint_text="z.B. links ins Bein",   expand=True)
        ai_aggravating       = ft.TextField(label="Verschlechterung",       hint_text="Kälte, Sitzen, Stress",       expand=True)
        ai_relieving         = ft.TextField(label="Linderung",              hint_text="Wärme, Massage, …",           expand=True)
        ai_func_limitations  = ft.TextField(label="Funktionelle Einschr.", hint_text="Gehstrecke, Sitztoleranz, …", expand=True)
        ai_additional_notes  = ft.TextField(label="Zusatzhinweise",         hint_text="Freier Text",                 expand=True, multiline=True, min_lines=2, max_lines=4)

        def on_ai_cluster_change(e: ft.ControlEvent) -> None:
            hints = _CLUSTER_HINTS.get(ai_cluster.value or "", _DEFAULT_HINTS)
            ai_pain_quality.hint_text   = hints["pain_quality"]
            ai_radiation.hint_text      = hints["radiation"]
            ai_aggravating.hint_text    = hints["aggravating"]
            ai_relieving.hint_text      = hints["relieving"]
            ai_func_limitations.hint_text = hints["func_limitations"]
            page.update()

        ai_cluster.on_change = on_ai_cluster_change
        # Apply hints for the initial cluster value
        on_ai_cluster_change(None)

        draft_result_field = ft.TextField(
            label="Generierter Entwurf (bearbeitbar)",
            multiline=True,
            min_lines=4,
            max_lines=10,
            expand=True,
        )
        draft_status = ft.Text("", size=12)

        debug_system_field = ft.TextField(
            label="SYSTEM PROMPT",
            multiline=True, min_lines=3, max_lines=8,
            read_only=True, expand=True,
        )
        debug_user_field = ft.TextField(
            label="USER PROMPT",
            multiline=True, min_lines=6, max_lines=16,
            read_only=True, expand=True,
        )
        debug_container = ft.Column(
            controls=[
                ft.Divider(height=16),
                ft.Text("Prompt-Debug", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.GREY_600),
                debug_system_field,
                ft.Container(height=8),
                debug_user_field,
            ],
            visible=False,
        )

        debug_checkbox = ft.Checkbox(
            label="Prompt-Debug anzeigen",
            value=False,
            on_change=lambda e: (
                setattr(debug_container, "visible", debug_checkbox.value),
                page.update(),
            ),
        )

        def on_draft_generate(e: ft.ControlEvent) -> None:
            def split_csv(val: str) -> list[str]:
                return [x.strip() for x in val.split(",") if x.strip()]

            inp = SymptomDraftInput(
                cluster             = ai_cluster.value or _cluster_default,
                duration            = ai_duration.value.strip() or None,
                pain_quality        = split_csv(ai_pain_quality.value),
                radiation           = ai_radiation.value.strip() or None,
                aggravating_factors  = split_csv(ai_aggravating.value),
                relieving_factors    = split_csv(ai_relieving.value),
                functional_limitations = split_csv(ai_func_limitations.value),
                additional_notes     = ai_additional_notes.value.strip() or None,
            )
            if debug_checkbox.value:
                style_config = _ai_svc.get_cluster_config(inp.cluster)
                debug_system_field.value = _ai_service._prompt_builder.build_system_prompt()
                debug_user_field.value   = _ai_service._prompt_builder.build_user_prompt(inp, style_config)

            try:
                result = _ai_service.generate_draft(inp)
                draft_result_field.value = result.main_text
                if result.validation.warnings:
                    draft_status.value = "\n".join(f"⚠ {w}" for w in result.validation.warnings)
                    draft_status.color = ft.Colors.ORANGE_700
                    draft_result_field.border_color = ft.Colors.ORANGE_700
                else:
                    draft_status.value = "✓ Validierung: OK"
                    draft_status.color = ft.Colors.GREEN_700
                    draft_result_field.border_color = ft.Colors.GREEN_700
            except Exception as exc:
                draft_status.value = f"Fehler: {exc}"
                draft_status.color = ft.Colors.RED_700
            page.update()

        def on_ai_apply(e: ft.ControlEvent) -> None:
            if not controller:
                return
            path = controller.state.schablone_path
            if path is None:
                draft_status.value = "Keine Schablone vorhanden."
                draft_status.color = ft.Colors.RED_700
                page.update()
                return
            draft_text = (draft_result_field.value or "").strip()
            if not draft_text:
                draft_status.value = "Bitte zuerst einen Entwurf generieren oder eingeben."
                draft_status.color = ft.Colors.ORANGE_700
                page.update()
                return
            try:
                insert_blocks_into_section(path, [draft_text])
                draft_status.value = "Text wurde in den Bericht übernommen."
                draft_status.color = ft.Colors.GREEN_700
            except Exception as exc:
                draft_status.value = f"Fehler beim Übernehmen: {exc}"
                draft_status.color = ft.Colors.RED_700
            page.update()

        def on_export(e: ft.ControlEvent) -> None:
            if not controller:
                return
            path = controller.state.schablone_path
            if path is None:
                export_status.value = "Keine Schablone vorhanden."
                export_status.color = ft.Colors.RED_700
                page.update()
                return

            if mode_selector.value == "AI-Entwurf-Modus":
                draft_text = draft_result_field.value.strip()
                if not draft_text:
                    export_status.value = "Bitte zuerst einen Entwurf generieren oder eingeben."
                    export_status.color = ft.Colors.ORANGE_700
                    page.update()
                    return
                try:
                    insert_blocks_into_section(path, [draft_text])
                    export_status.value = "Entwurf wurde in die Aufnahme übernommen."
                    export_status.color = ft.Colors.GREEN_700
                except Exception as exc:
                    export_status.value = f"Datei konnte nicht gespeichert werden: {exc}"
                    export_status.color = ft.Colors.RED_700
                page.update()
                return

            # Block-Modus — stávající chování beze změny
            blocks = controller.state.composed_blocks
            if not blocks:
                export_status.value = "Keine Textblöcke ausgewählt."
                export_status.color = ft.Colors.ORANGE_700
                page.update()
                return
            try:
                insert_blocks_into_section(path, blocks)
                controller.state.composed_blocks.clear()
                refresh_blocks_column()
                export_status.value = "Text wurde in die Aufnahme übernommen."
                export_status.color = ft.Colors.GREEN_700
            except Exception as exc:
                export_status.value = f"Datei konnte nicht gespeichert werden: {exc}"
                export_status.color = ft.Colors.RED_700
            page.update()

        # --- Mode switcher ---
        block_mode_container = ft.Column(
            controls=[
                symptom_group,
                ft.Container(height=8),
                fields_container,
                ft.Container(height=12),
                ft.ElevatedButton("Text generieren", on_click=on_generate),
                ft.Container(height=16),
                result_column,
                ft.Divider(height=24),
                ft.Text("Ausgewählte Textblöcke", weight=ft.FontWeight.BOLD, size=14),
                ft.Container(height=8),
                blocks_column,
                ft.Container(height=8),
                ft.ElevatedButton("In Aufnahme übernehmen", on_click=on_export),
                ft.Container(height=4),
                export_status,
            ],
            visible=True,
        )

        ai_draft_container = ft.Column(
            controls=[
                ft.Row(controls=[ai_cluster, ai_duration],       spacing=12),
                ft.Row(controls=[ai_pain_quality, ai_radiation], spacing=12),
                ft.Row(controls=[ai_aggravating, ai_relieving],          spacing=12),
                ft.Row(controls=[ai_func_limitations, ai_additional_notes], spacing=12),
                ft.Container(height=12),
                debug_checkbox,
                ft.Row(controls=[
                    ft.ElevatedButton("Draft generieren",    on_click=on_draft_generate),
                    ft.ElevatedButton("In Bericht übernehmen", on_click=on_ai_apply),
                ], spacing=12),
                ft.Container(height=12),
                draft_result_field,
                ft.Container(height=4),
                draft_status,
                debug_container,
            ],
            visible=False,
        )

        def on_mode_change(e: ft.ControlEvent) -> None:
            is_ai = mode_selector.value == "AI-Entwurf-Modus"
            block_mode_container.visible = not is_ai
            ai_draft_container.visible   = is_ai
            page.update()

        mode_selector = ft.Dropdown(
            label="Modus",
            value="Block-Modus",
            options=[
                ft.dropdown.Option("Block-Modus"),
                ft.dropdown.Option("AI-Entwurf-Modus"),
            ],
            width=240,
            on_change=on_mode_change,
        )

        composer_column = ft.Column(
            controls=[
                ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
                ft.Container(height=12),
                mode_selector,
                ft.Container(height=12),
                block_mode_container,
                ai_draft_container,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        # --- Prefill AI draft from CaseSummary ---
        if self._summary and self._summary.most_burdensome:
            _cluster_val = self._summary.most_burdensome.strip()
            _notes_parts = [
                self._summary.priority_complaint,
                self._summary.additional_complaints,
            ]
            _additional = ", ".join(p for p in _notes_parts if p and p.strip())
            _inp = SymptomDraftInput(
                cluster          = _cluster_val if _cluster_val in _cluster_names else _cluster_default,
                additional_notes = _additional or None,
            )
            try:
                _result = _ai_service.generate_draft(_inp)
                draft_result_field.value = _result.main_text
                mode_selector.value         = "AI-Entwurf-Modus"
                block_mode_container.visible = False
                ai_draft_container.visible   = True
                if _result.validation.warnings:
                    draft_status.value = "\n".join(f"⚠ {w}" for w in _result.validation.warnings)
                    draft_status.color = ft.Colors.ORANGE_700
                    draft_result_field.border_color = ft.Colors.ORANGE_700
                else:
                    draft_status.value = "✓ Validierung: OK"
                    draft_status.color = ft.Colors.GREEN_700
                    draft_result_field.border_color = ft.Colors.GREEN_700
            except Exception:
                pass  # silent — neblokuje otevření screenu

        if self._summary:
            page.add(ft.Row(
                controls=[composer_column, SummaryPanel(self._summary).build()],
                spacing=24,
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=True,
            ))
        else:
            page.add(composer_column)
