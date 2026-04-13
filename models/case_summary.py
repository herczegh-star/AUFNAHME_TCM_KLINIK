"""
case_summary.py
---------------
Data models for application state and case summary.

CaseSummary: collected interview answers (Screen 2), passed to PilotComposer.
AppState: owned by AppController, shared across all screens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CaseSummary:
    """
    Working clinical compass produced by the psychosomatic interview (Screen 2).

    primary_clusters and secondary_clusters are SUGGESTIONS ONLY.
    Final clinical decisions remain with the physician.
    """
    # Raw interview answers
    main_complaints:       str = ""   # Q1: körperliche Beschwerden
    most_burdensome:       str = ""   # Q2: belastet im Alltag am meisten
    priority_complaint:    str = ""   # Q3: sofort loswerden
    additional_complaints: str = ""   # Q4: weitere Beschwerden

    # Derived hints — physician may ignore, override or discard entirely
    primary_clusters:   list[str] = field(default_factory=list)  # 1–2 cluster names
    secondary_clusters: list[str] = field(default_factory=list)  # 2–3 cluster names
    remaining_notes:    str = ""


@dataclass
class AppState:
    """
    Central application state passed between screens via AppController.

    Phase 1: defined here, not yet used at runtime.
    Phase 2: instantiated and owned by AppController.
    """
    # Navigation
    current_screen: int | str = 1              # 1 | 2 | "summary_review" | 3

    # Screen 1
    schablone_generated: bool = False
    schablone_path: Path | None = None

    # Screen 2 → 3 transition
    summary: CaseSummary = field(default_factory=CaseSummary)

    # Screen 3 — active working state
    selected_cluster_id: str = ""
    active_form_data: dict[str, str] = field(default_factory=dict)

    # Generated text blocks — physician selects from these
    composed_blocks: list[str] = field(default_factory=list)

    # Pilot-Composer working-state snapshot (saved on "Speichern und verlassen").
    # Keys: text (str), composer_state (str), storage_key (str).
    # Cleared automatically after restore on re-entry.
    pilot_draft: dict | None = None

    # Sequential block composition state.
    # block_sequence: list of dicts with keys complaint (str), storage_key (str), accepted (bool).
    # Built from most_burdensome + priority_complaint in show_screen_2b().
    # active_block_index: which block the Pilot-Composer is currently working on.
    block_sequence: list[dict] = field(default_factory=list)
    active_block_index: int = 0

    # Candidate pool for block 3+ physician-driven selection.
    # Built from additional_complaints in show_screen_2b().
    # Each entry: {"complaint": str, "storage_key": str, "dismissed": bool}
    # The physician promotes one candidate at a time; dismissed=True removes it from view.
    candidate_pool: list[dict] = field(default_factory=list)
