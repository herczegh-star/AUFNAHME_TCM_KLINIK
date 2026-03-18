from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Cluster anchors for structured mode (no pre-written text)
# ---------------------------------------------------------------------------

_CLUSTER_ANCHORS: dict[str, str] = {
    "lws_syndrom":
        "Der Patient berichtet seit vielen Jahren über Schmerzen im LWS-Bereich.",
    "hws_syndrom":
        "Der Patient berichtet seit vielen Jahren über Schmerzen im HWS-Bereich.",
    "ws_syndrom":
        "Der Patient berichtet seit vielen Jahren über Beschwerden im Bereich der Wirbelsäule.",
    "fibromyalgie_ganzkoerperschmerzen":
        "Der Patient berichtet seit vielen Jahren über chronische Schmerzen im Sinne einer Fibromyalgie.",
    "kopfschmerzen":
        "Der Patient berichtet seit vielen Jahren über rezidivierende Kopfschmerzen.",
    "migraene":
        "Der Patient berichtet seit vielen Jahren über rezidivierende Migräneattacken.",
    "reizdarm_funktionelle_verdauungsbeschwerden":
        "Der Patient berichtet seit vielen Jahren über Beschwerden im Sinne eines Reizdarmsyndroms.",
    "ced_ibd":
        "Der Patient berichtet über eine bekannte chronisch entzündliche Darmerkrankung.",
    "tinnitus_aurium":
        "Der Patient berichtet seit vielen Jahren über einen Tinnitus aurium.",
    "muedigkeit":
        "Der Patient berichtet seit vielen Jahren über chronische Erschöpfung und ausgeprägte Müdigkeit.",
}


def _generate_anchor(cluster_id: str, cluster_name: str) -> str:
    return _CLUSTER_ANCHORS.get(
        cluster_id,
        f"Der Patient berichtet seit vielen Jahren über Beschwerden im Sinne eines {cluster_name}.",
    )


# ---------------------------------------------------------------------------
# Cluster dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Cluster:
    """
    Represents one symptom cluster from template_library_v2.json.

    Backward-compatible with the old Template dataclass via .section,
    .title and .text properties — so ui/app.py requires no changes.
    """
    id: str
    name: str
    type: str
    mode: str                                   # "structured" | "template" | "variant"
    meta: dict         = field(default_factory=dict,  compare=False, hash=False)
    struktur: tuple    = field(default_factory=tuple, compare=False, hash=False)
    slot_options: dict = field(default_factory=dict,  compare=False, hash=False)
    templates: tuple   = field(default_factory=tuple, compare=False, hash=False)
    varianty: tuple    = field(default_factory=tuple, compare=False, hash=False)

    # --- backward-compat interface for UI ---

    @property
    def section(self) -> str:
        return self.id

    @property
    def title(self) -> str:
        return self.name

    @property
    def text(self) -> str:
        """
        Representative text for this cluster:
        - template mode  → first pre-written template (may contain [placeholders])
        - structured mode → generated anchor sentence
        - variant mode   → generated anchor sentence
        """
        if self.mode == "template" and self.templates:
            return self.templates[0]
        return _generate_anchor(self.id, self.name)


# Keep old name as alias so existing imports still work
Template = Cluster


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class TemplateRepository:
    _DATA_PATH = Path(__file__).parent.parent / "data" / "template_library_v2.json"

    def __init__(self) -> None:
        self._clusters: list[Cluster] = []

    def load_templates(self) -> None:
        with self._DATA_PATH.open(encoding="utf-8-sig") as f:
            raw: dict = json.load(f)

        self._clusters = []
        for entry in raw.get("clustery", []):
            if entry.get("type") != "symptom_cluster":
                continue

            # For structured mode: collect per-slot option lists
            struktur: list[str] = entry.get("struktur", [])
            slot_options: dict[str, list[str]] = {}
            for slot in struktur:
                if slot in entry and isinstance(entry[slot], list):
                    slot_options[slot] = entry[slot]

            self._clusters.append(Cluster(
                id=entry["id"],
                name=entry["name"],
                type=entry["type"],
                mode=entry["mode"],
                meta=entry.get("meta", {}),
                struktur=tuple(struktur),
                slot_options=slot_options,
                templates=tuple(entry.get("templates", [])),
                varianty=tuple(entry.get("varianty", [])),
            ))

    def get_all_templates(self) -> list[Cluster]:
        return list(self._clusters)

    def get_templates_by_section(self, section: str) -> list[Cluster]:
        return [c for c in self._clusters if c.id == section or c.name == section]

    def search_by_keyword(self, keyword: str) -> list[Cluster]:
        kw = keyword.lower()
        return [c for c in self._clusters if kw in c.name.lower()]
