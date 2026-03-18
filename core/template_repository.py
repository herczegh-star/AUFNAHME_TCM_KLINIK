from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Cluster anchors for structured / variant mode (no pre-written text)
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
    # variant mode — anchor selected dynamically in symptom_composer
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
    mode: str                                    # "structured" | "template" | "variant"
    meta: dict         = field(default_factory=dict,  compare=False, hash=False)
    struktur: tuple    = field(default_factory=tuple, compare=False, hash=False)
    slot_options: dict = field(default_factory=dict,  compare=False, hash=False)
    templates: tuple   = field(default_factory=tuple, compare=False, hash=False)
    varianty: tuple    = field(default_factory=tuple, compare=False, hash=False)
    diagnosen: tuple   = field(default_factory=tuple, compare=False, hash=False)

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
        Representative text for this cluster passed to symptom_composer.

        - template mode  → first pre-written template, with [diagnose]
                           pre-filled from diagnosen[0] if available.
                           [dauer] and [lokalisation] left for composer.
        - structured mode → cluster-specific anchor sentence
        - variant mode   → anchor sentence; composer selects variant
        """
        if self.mode == "template" and self.templates:
            t = self.templates[0]
            if self.diagnosen:
                t = re.sub(r"\[diagnose\]", self.diagnosen[0], t, flags=re.IGNORECASE)
            return t
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
                diagnosen=tuple(entry.get("diagnosen", [])),
            ))

    def get_all_templates(self) -> list[Cluster]:
        return list(self._clusters)

    def get_templates_by_section(self, section: str) -> list[Cluster]:
        return [c for c in self._clusters if c.id == section or c.name == section]

    def search_by_keyword(self, keyword: str) -> list[Cluster]:
        kw = keyword.lower()
        return [c for c in self._clusters if kw in c.name.lower()]
