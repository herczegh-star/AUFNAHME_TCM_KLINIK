import sys
from pathlib import Path

print("Python executable:", sys.executable)
print("Python version:", sys.version)

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft

from core.template_repository import Cluster
from core.symptom_composer import compose_symptom_text
from core.language_refiner import refine_clinical_german
from services.pipeline_service import PipelineService


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

# ---------------------------------------------------------------------------
# Slot → form field mapping
# Each v2 struktur slot maps to: (German label, form_data_key)
# Multiple slots may share a form_data_key — only the first shown per key.
# ---------------------------------------------------------------------------

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

# Default fields for template / variant mode (no struktur)
DEFAULT_FIELD_DEFS: list[tuple[str, str, str]] = [
    ("Dauer",           "dauer",            "z.B. seit 5 Jahren"),
    ("Verlauf",         "verlauf",          "z.B. progredient, fluktuierend"),
    ("Charakter",       "charakter",        "z.B. stechend, brennend"),
    ("Verschlechterung","verschlechterung", "z.B. Stress, Belastung"),
    ("Linderung",       "linderung",        "z.B. Wärme, Ruhe"),
    ("Begleitsymptome", "begleitsymptome",  "z.B. Übelkeit, Kribbeln"),
]


def main(page: ft.Page) -> None:
    page.title = "AUFNAHME TCM KLINIK"
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO

    matcher, llm, repo = PipelineService().build()

    # --- State ---
    active_fields: dict[str, ft.TextField] = {}   # form_data_key → TextField
    fields_container = ft.Column(spacing=8)
    result_column = ft.Column(spacing=16)

    # --- Field builder ---
    def rebuild_fields(cluster: Cluster | None) -> None:
        """Rebuild form fields based on the selected cluster's struktur."""
        active_fields.clear()
        field_defs: list[tuple[str, str, str]] = []  # (label, form_key, hint)

        if cluster and cluster.mode == "structured" and cluster.struktur:
            seen_keys: set[str] = set()
            for slot in cluster.struktur:
                if slot not in SLOT_TO_FIELD:
                    continue
                label, form_key = SLOT_TO_FIELD[slot]
                if form_key in seen_keys:
                    continue
                seen_keys.add(form_key)
                # Build hint from cluster slot options (first 3 values)
                options = cluster.slot_options.get(slot, [])
                hint = ", ".join(options[:3]) if options else ""
                field_defs.append((label, form_key, hint))
        else:
            field_defs = DEFAULT_FIELD_DEFS

        # Create TextField widgets
        for label, form_key, hint in field_defs:
            tf = ft.TextField(label=label, hint_text=hint, expand=True)
            active_fields[form_key] = tf

        # Layout: pairs of fields in rows
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

    # Initialize with default empty fields
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


ft.app(target=main)
