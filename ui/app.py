import sys
from pathlib import Path

print("Python executable:", sys.executable)
print("Python version:", sys.version)

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft

from core.template_repository import TemplateRepository
from core.embedding_index import EmbeddingIndex
from core.template_matcher import TemplateMatcher
from core.symptom_composer import compose_symptom_text
from core.language_refiner import refine_clinical_german, OpenAIRefinerClient


SYMPTOM_GROUPS = [
    "EINLEITUNG",
    "LWS-Syndrom",
    "HWS-Syndrom",
    "Fibromyalgie / Ganzkörperschmerzen",
    "Kopfschmerzen",
    "Migräne",
    "Reizdarm / funktionelle Verdauungsbeschwerden",
    "CED / IBD",
    "Tinnitus aurium",
]


def build_pipeline() -> tuple[TemplateMatcher, OpenAIRefinerClient | None]:
    repo = TemplateRepository()
    repo.load_templates()
    index = EmbeddingIndex()
    index.build_index(repo.get_all_templates())
    try:
        llm = OpenAIRefinerClient()
    except Exception:
        llm = None
    return TemplateMatcher(repo, index), llm


def main(page: ft.Page) -> None:
    page.title = "AUFNAHME TCM KLINIK"
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO

    matcher, llm = build_pipeline()

    # --- Form fields ---
    symptom_group = ft.Dropdown(
        label="Symptomgruppe",
        options=[ft.dropdown.Option(g) for g in SYMPTOM_GROUPS],
        expand=True,
    )
    duration       = ft.TextField(label="Dauer", hint_text="z.B. seit 5 Jahren")
    character      = ft.TextField(label="Charakter", hint_text="z.B. stechend, dumpf")
    radiation      = ft.TextField(label="Ausstrahlung", hint_text="z.B. ins linke Bein")
    side           = ft.TextField(label="Seite / Betonung", hint_text="z.B. linksbetont")
    aggravating    = ft.TextField(label="Verschlechterung", hint_text="z.B. bei Belastung")
    relieving      = ft.TextField(label="Linderung", hint_text="z.B. Wärme, Ruhe")
    associated     = ft.TextField(label="Begleitsymptome", hint_text="z.B. Übelkeit, Kribbeln")
    progression    = ft.TextField(label="Verlauf", hint_text="z.B. progredient, fluktuierend")

    result_column = ft.Column(spacing=16)

    def on_generate(e: ft.ControlEvent) -> None:
        group = symptom_group.value or ""
        form_data = {
            "dauer":            duration.value.strip(),
            "verlauf":          progression.value.strip(),
            "charakter":        character.value.strip(),
            "seite":            side.value.strip(),
            "ausstrahlung":     radiation.value.strip(),
            "verschlechterung": aggravating.value.strip(),
            "linderung":        relieving.value.strip(),
            "begleitsymptome":  associated.value.strip(),
        }

        query = " ".join(filter(None, [
            group,
            form_data["dauer"],
            form_data["charakter"],
            form_data["verlauf"],
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

    page.add(
        ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
        ft.Container(height=12),
        symptom_group,
        ft.Container(height=8),
        ft.Row(controls=[duration, character], spacing=12),
        ft.Row(controls=[progression, side], spacing=12),
        ft.Row(controls=[radiation, aggravating], spacing=12),
        ft.Row(controls=[relieving, associated], spacing=12),
        ft.Container(height=12),
        ft.ElevatedButton("Text generieren", on_click=on_generate),
        ft.Container(height=16),
        result_column,
    )


ft.app(target=main)
