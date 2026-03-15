from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Template:
    section: str
    title: str
    text: str


class TemplateRepository:
    _DATA_PATH = Path(__file__).parent.parent / "data" / "template_library.json"

    def __init__(self) -> None:
        self._templates: list[Template] = []

    def load_templates(self) -> None:
        with self._DATA_PATH.open(encoding="utf-8") as f:
            raw: list[dict] = json.load(f)
        self._templates = [
            Template(
                section=entry["section"],
                title=entry["title"],
                text=entry["text"],
            )
            for entry in raw
        ]

    def get_all_templates(self) -> list[Template]:
        return list(self._templates)

    def get_templates_by_section(self, section: str) -> list[Template]:
        return [t for t in self._templates if t.section == section]

    def search_by_keyword(self, keyword: str) -> list[Template]:
        keyword_lower = keyword.lower()
        return [
            t for t in self._templates
            if keyword_lower in t.title.lower() or keyword_lower in t.text.lower()
        ]
