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


class ScreenComposer:
    """
    Composer screen.
    Receives page and pipeline from AppController — builds nothing itself.
    """

    def __init__(
        self,
        page: ft.Page,
        pipeline: tuple[TemplateMatcher, OpenAIRefinerClient | None, TemplateRepository],
    ) -> None:
        self._page = page
        self._matcher, self._llm, self._repo = pipeline

    def render(self) -> None:
        page    = self._page
        matcher = self._matcher
        llm     = self._llm
        repo    = self._repo

        # --- State ---
        active_fields: dict[str, ft.TextField] = {}
        fields_container = ft.Column(spacing=8)
        result_column = ft.Column(spacing=16)

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
                                    ft.ElevatedButton("Kopieren", on_click=make_copy_handler(filled_text)),
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

        page.add(
            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            symptom_group,
            ft.Container(height=8),
            fields_container,
            ft.Container(height=12),
            ft.ElevatedButton("Text generieren", on_click=on_generate),
            ft.Container(height=16),
            result_column,
        )
