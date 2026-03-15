import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft

from core.template_repository import TemplateRepository
from core.embedding_index import EmbeddingIndex
from core.template_matcher import TemplateMatcher


def build_pipeline() -> TemplateMatcher:
    repo = TemplateRepository()
    repo.load_templates()
    index = EmbeddingIndex()
    index.build_index(repo.get_all_templates())
    return TemplateMatcher(repo, index)


def main(page: ft.Page) -> None:
    page.title = "AUFNAHME TCM KLINIK"
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO

    matcher = build_pipeline()

    query_field = ft.TextField(
        label="Symptom-Beschreibung",
        multiline=True,
        min_lines=2,
        max_lines=5,
        expand=True,
    )

    results_column = ft.Column(spacing=16)

    def on_search(e: ft.ControlEvent) -> None:
        query = query_field.value.strip()
        if not query:
            return

        templates = matcher.find_best_templates(query, top_k=3)
        results_column.controls.clear()

        for i, t in enumerate(templates, 1):
            results_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Text(f"{i}. {t.title}", weight=ft.FontWeight.BOLD, size=14),
                                ft.Text(t.section, color=ft.Colors.GREY_600, size=12),
                                ft.Divider(height=1),
                                ft.Text(t.text, size=13, selectable=True),
                            ],
                        ),
                    )
                )
            )

        page.update()

    page.add(
        ft.Text("Template-Finder", size=22, weight=ft.FontWeight.BOLD),
        ft.SizedBox(height=8),
        ft.Row(
            controls=[
                query_field,
                ft.ElevatedButton("Template finden", on_click=on_search),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        ft.SizedBox(height=16),
        results_column,
    )


ft.app(target=main)
