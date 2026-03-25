"""
rule_engine.py
--------------
Lightweight compositional rule engine for the AI-Draft pipeline.

Validates and cleans a selected set of blocks before they reach
the draft composer.

This is a protective layer — not a clinical expert system.
It enforces structural and compositional constraints defined in the block model.

Does NOT perform:
- clinical inference
- heuristic scoring
- language composition
- AI refinement

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md  (STEP 5)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.ai_draft.block_model import Block, BlockType


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RuleEngineResult:
    """
    Output of the rule engine.

    is_valid:   False if any critical violation was found that cannot be auto-fixed.
    blocks:     Cleaned block list after all auto-corrections have been applied.
    violations: Human-readable descriptions of all issues found (fixed or not).
    """
    is_valid:   bool
    blocks:     list[Block]         = field(default_factory=list)
    violations: list[str]           = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

class RuleEngine:
    """
    Applies composition rules to a list of selected blocks.

    Rules:
      R01  At least one CORE_SYMPTOM must be present          [violation only]
      R02  No forbidden_with pair may coexist                  [auto-fix: drop]
      R03  Every requires constraint must be satisfied         [auto-fix: drop]
      R04  No two blocks may have the same semantic fingerprint[auto-fix: drop]
    """

    def validate(self, blocks: list[Block]) -> RuleEngineResult:
        """
        Run all rules against the input block list.
        Returns a RuleEngineResult with cleaned blocks and recorded violations.
        """
        violations: list[str] = []
        current = list(blocks)

        # Auto-fix rules (order matters: remove forbidden first, then re-check requires)
        current, v02 = self._rule_forbidden(current)
        violations.extend(v02)

        current, v03 = self._rule_requires(current)
        violations.extend(v03)

        current, v04 = self._rule_no_duplicates(current)
        violations.extend(v04)

        # Violation-only rules (run after cleaning)
        v01 = self._rule_requires_core(current)
        violations.extend(v01)

        is_valid = len(v01) == 0  # critical: no CORE means draft cannot be composed
        return RuleEngineResult(
            is_valid=is_valid,
            blocks=current,
            violations=violations,
        )

    # ------------------------------------------------------------------
    # R01 — at least one CORE_SYMPTOM  [violation only]
    # ------------------------------------------------------------------

    def _rule_requires_core(self, blocks: list[Block]) -> list[str]:
        """
        R01: A valid draft requires at least one CORE_SYMPTOM block.
        Cannot be auto-fixed — the selection input was insufficient.
        """
        has_core = any(b.type == BlockType.CORE_SYMPTOM for b in blocks)
        if not has_core:
            return [
                "R01: Kein CORE_SYMPTOM-Block vorhanden. "
                "Ein Draft ohne Hauptbeschwerde kann nicht erstellt werden."
            ]
        return []

    # ------------------------------------------------------------------
    # R02 — no forbidden_with pairs  [auto-fix: drop lower-priority block]
    # ------------------------------------------------------------------

    def _rule_forbidden(self, blocks: list[Block]) -> tuple[list[Block], list[str]]:
        """
        R02: No two selected blocks may appear in each other's forbidden_with list.

        Resolution: blocks are processed in input order (CORE first).
        The first conflicting block keeps its place; the later one is dropped.
        """
        kept:     list[Block] = []
        kept_ids: set[str]    = set()
        violations: list[str] = []

        for block in blocks:
            conflict_ids = {f for f in block.composition.forbidden_with} & kept_ids
            reverse_conflicts = {
                b.id for b in kept if block.id in b.composition.forbidden_with
            }
            all_conflicts = conflict_ids | reverse_conflicts

            if all_conflicts:
                violations.append(
                    f"R02: Block '{block.id}' kollidiert mit bereits ausgewähltem "
                    f"Block(s) {sorted(all_conflicts)} (forbidden_with). "
                    f"Block '{block.id}' wurde entfernt."
                )
            else:
                kept.append(block)
                kept_ids.add(block.id)

        return kept, violations

    # ------------------------------------------------------------------
    # R03 — requires satisfied  [auto-fix: drop unsatisfied block]
    # ------------------------------------------------------------------

    def _rule_requires(self, blocks: list[Block]) -> tuple[list[Block], list[str]]:
        """
        R03: Every block whose requires list is non-empty must have
        at least one required block present in the set (OR logic).

        Blocks with empty requires are always valid.
        """
        present_ids = {b.id for b in blocks}
        kept:       list[Block] = []
        violations: list[str]   = []

        for block in blocks:
            req = block.composition.requires
            if req and not any(r in present_ids for r in req):
                violations.append(
                    f"R03: Block '{block.id}' benötigt mindestens einen dieser Blöcke: "
                    f"{req}. Keiner ist vorhanden. Block wurde entfernt."
                )
            else:
                kept.append(block)

        return kept, violations

    # ------------------------------------------------------------------
    # R04 — no duplicate semantic meaning  [auto-fix: drop later block]
    # ------------------------------------------------------------------

    def _rule_no_duplicates(self, blocks: list[Block]) -> tuple[list[Block], list[str]]:
        """
        R04: No two blocks may share the same semantic fingerprint.

        Fingerprint per block type:
          CORE_SYMPTOM      → (type, localisation, side)
          MODIFIER/char     → (type, modifier_type, value)
          MODIFIER/other    → (type, modifier_type, trigger)
          FUNCTIONAL_IMPACT → (type, limitation_type)
          ASSOCIATED_SYMPTOM→ (type, symptom)
          others            → (type, id)   — id is always unique, so no dedup
        """
        seen:       set[tuple] = set()
        kept:       list[Block] = []
        violations: list[str]   = []

        for block in blocks:
            fp = self._fingerprint(block)
            if fp in seen:
                violations.append(
                    f"R04: Block '{block.id}' hat denselben semantischen Fingerabdruck "
                    f"{fp} wie ein bereits ausgewählter Block. Duplikat entfernt."
                )
            else:
                seen.add(fp)
                kept.append(block)

        return kept, violations

    # ------------------------------------------------------------------
    # Private: semantic fingerprint
    # ------------------------------------------------------------------

    def _fingerprint(self, block: Block) -> tuple:
        t = block.type
        s = block.semantic

        if t == BlockType.CORE_SYMPTOM:
            return (t, s.get("localisation"), s.get("side"))

        if t == BlockType.MODIFIER:
            mod = s.get("modifier_type", "")
            if mod == "character":
                return (t, mod, s.get("value"))
            if mod in ("aggravating_factor", "relieving_factor"):
                return (t, mod, s.get("trigger"))
            if mod == "radiation":
                return (t, mod, s.get("target_region"))
            return (t, mod, s.get("value"))

        if t == BlockType.FUNCTIONAL_IMPACT:
            return (t, s.get("limitation_type"))

        if t == BlockType.ASSOCIATED_SYMPTOM:
            return (t, s.get("symptom"))

        # CONTEXT, TEMPORAL, EXPERT — fall back to id (no dedup)
        return (t, block.id)
