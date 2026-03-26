"""
shared_pain_selector.py
-----------------------
Maps normalized_input values to concrete shared pain item canonicals.

Philosophy (AI_DRAFT_CONTENT_PHILOSOPHY.md):
- Select only what has an explicit input signal — never fill speculatively
- Overlays (neuro_sensory, cephalgic_features) only fire when associated_symptoms present
- Respect max_select per module — prefer core-priority items when truncating
- No diagnostic reasoning, no automatic expansion

ORDER CONVENTION — two distinct layers:

  1. Internal deterministic order (this module's responsibility):
     - dict keys:   alphabetical by module name
     - list values: alphabetical by canonical within each module
     - Purpose: stable output for tests, serialization, diff, debug
     - This order carries NO clinical meaning

  2. Clinical narrative order (composer's responsibility, NOT here):
     - e.g. "character before laterality", "aggravating before relieving"
     - cluster-aware, pattern-aware, linguistically motivated
     - must NOT be imposed at selection time

API:
    selector = SharedPainSelector()
    result   = selector.select_items("lws_syndrom", normalized_input)

Returns:
    {
      "aggravating_mechanical":  ["langes_sitzen"],   # keys: alpha
      "pain_character":          ["stechend", "ziehend"],  # values: alpha
      "pain_laterality":         ["beidseits"],
      "relieving_passive":       ["waerme"],
      ...
    }

Only modules with ≥1 match are present in the output dict.
"""

from __future__ import annotations

from typing import Any

from core.ai_draft.shared_pain_loader import (
    get_family_allowed_modules,
    get_module_definition,
)


# ---------------------------------------------------------------------------
# Alias maps: normalized display value → shared_layer canonical id
# ---------------------------------------------------------------------------

# pain_character: InputNormalizer already returns canonical strings,
# but uses display casing — lowercase comparison is sufficient.
_CHARACTER_TO_CANONICAL: dict[str, str] = {
    "ziehend":        "ziehend",
    "stechend":       "stechend",
    "dumpf":          "dumpf",
    "brennend":       "brennend",
    "krampfartig":    "krampfartig",
    "drückend":       "drueckend",    # normalizer canonical → shared id
    "drueckend":      "drueckend",
    "elektrisierend": "elektrisierend",
    "pulsierend":     "pulsierend",
}

# aggravating: normalized display form (post-InputNormalizer) → shared canonical
_AGG_MECH_TO_CANONICAL: dict[str, str] = {
    "langes sitzen":  "langes_sitzen",
    "langes stehen":  "langes_stehen",
    "langes gehen":   "langes_gehen",
    "bücken":         "buecken",
    "buecken":        "buecken",
    "treppensteigen": "treppensteigen",
    "belastung":      "belastung",
}

_AGG_GENERAL_TO_CANONICAL: dict[str, str] = {
    "kälte":   "kaelte",
    "kaelte":  "kaelte",
    "stress":  "stress",
}

# relieving: post-InputNormalizer → shared canonical
_REL_PASSIVE_TO_CANONICAL: dict[str, str] = {
    "wärme":     "waerme",
    "waerme":    "waerme",
    "ruhe":      "ruhe",
    "liegen":    "liegen",
    "bewegung":  "bewegung",
}

_REL_THERAPY_TO_CANONICAL: dict[str, str] = {
    "krankengymnastik":  "krankengymnastik",
    "manuelle therapie": "manuelle_therapie",
    "manuelle_therapie": "manuelle_therapie",
    "massage":           "massage",
    "dehnung":           "dehnung",
    "akupunktur":        "akupunktur",
}

# functional limitations: InputNormalizer already produces canonical ids
_FUNC_MOBILITY: frozenset[str] = frozenset({
    "sitting_tolerance", "walking_distance", "bending", "lifting",
})

_FUNC_GENERAL: frozenset[str] = frozenset({
    "sleep_quality", "daily_function", "general_capacity",
})

# neuro_sensory: associated_symptom substrings → shared canonical
_NEURO_SENSORY_TO_CANONICAL: dict[str, str] = {
    "kribbeln":      "kribbeln",
    "taubheit":      "taubheit",
    "paraesthesien": "paraesthesien",
    "parästhesien":  "paraesthesien",
    "taubheitsgefühl": "taubheit",
    "kribbelgefühl": "kribbeln",
}

# cephalgic_features: associated_symptom substrings → shared canonical
_CEPHALIC_TO_CANONICAL: dict[str, str] = {
    "uebelkeit":              "uebelkeit",
    "übelkeit":               "uebelkeit",
    "lichtempfindlichkeit":   "lichtempfindlichkeit",
    "lärmempfindlichkeit":    "laermempfindlichkeit",
    "laermempfindlichkeit":   "laermempfindlichkeit",
}

# radiation_target values accepted directly
_RADIATION_TARGETS: frozenset[str] = frozenset({
    "Bein", "Gesäß", "Arm", "Schulter", "Leiste", "Unterbauch",
})


# ---------------------------------------------------------------------------
# Public selector
# ---------------------------------------------------------------------------

class SharedPainSelector:
    """
    Selects concrete shared pain item canonicals from normalized_input.

    Selection is input-driven: only items with an explicit signal in
    normalized_input are returned. No speculative expansion.
    """

    def select_items(
        self,
        cluster_id:       str,
        normalized_input: dict[str, Any],
    ) -> dict[str, list[str]]:
        """
        Map normalized_input to shared pain item canonicals.

        Returns dict of {module_name: [canonical, ...]} for modules
        with at least one match. Empty modules are omitted.
        Only selects from modules allowed for the cluster's pain family.

        Output order (internal deterministic convention):
          - dict keys:   sorted alphabetically by module name
          - list values: sorted alphabetically by canonical
          This order is stable for tests, serialization and debug.
          It carries NO clinical meaning — narrative order is the
          composer's responsibility.
        """
        allowed = get_family_allowed_modules(cluster_id)
        raw:  dict[str, list[str]] = {}

        # ── pain_character ───────────────────────────────────────────────
        if "pain_character" in allowed:
            items = self._select_character(normalized_input)
            if items:
                raw["pain_character"] = items

        # ── pain_laterality ──────────────────────────────────────────────
        if "pain_laterality" in allowed:
            items = self._select_laterality(normalized_input)
            if items:
                raw["pain_laterality"] = items

        # ── aggravating_mechanical ───────────────────────────────────────
        if "aggravating_mechanical" in allowed:
            items = self._select_aggravating_mechanical(normalized_input)
            if items:
                raw["aggravating_mechanical"] = items

        # ── aggravating_general ──────────────────────────────────────────
        if "aggravating_general" in allowed:
            items = self._select_aggravating_general(normalized_input)
            if items:
                raw["aggravating_general"] = items

        # ── relieving_passive ────────────────────────────────────────────
        if "relieving_passive" in allowed:
            items = self._select_relieving_passive(normalized_input)
            if items:
                raw["relieving_passive"] = items

        # ── relieving_therapy ────────────────────────────────────────────
        if "relieving_therapy" in allowed:
            items = self._select_relieving_therapy(normalized_input)
            if items:
                raw["relieving_therapy"] = items

        # ── pain_radiation ───────────────────────────────────────────────
        if "pain_radiation" in allowed:
            items = self._select_radiation(normalized_input)
            if items:
                raw["pain_radiation"] = items

        # ── functional_mobility ──────────────────────────────────────────
        if "functional_mobility" in allowed:
            items = self._select_functional(normalized_input, _FUNC_MOBILITY, "functional_mobility")
            if items:
                raw["functional_mobility"] = items

        # ── functional_general ───────────────────────────────────────────
        if "functional_general" in allowed:
            items = self._select_functional(normalized_input, _FUNC_GENERAL, "functional_general")
            if items:
                raw["functional_general"] = items

        # ── neuro_sensory (overlay: only on explicit input) ──────────────
        if "neuro_sensory" in allowed:
            items = self._select_associated_mapped(
                normalized_input, _NEURO_SENSORY_TO_CANONICAL, "neuro_sensory"
            )
            if items:
                raw["neuro_sensory"] = items

        # ── cephalgic_features (overlay: only on explicit input) ─────────
        if "cephalgic_features" in allowed:
            items = self._select_associated_mapped(
                normalized_input, _CEPHALIC_TO_CANONICAL, "cephalgic_features"
            )
            if items:
                raw["cephalgic_features"] = items

        # ── Apply internal deterministic order ───────────────────────────
        # Keys: alphabetical. Values: alphabetical within each list.
        # This is NOT clinical narrative order — that belongs to the composer.
        return {
            key: sorted(raw[key])
            for key in sorted(raw)
        }

    # ------------------------------------------------------------------
    # Private: per-module selectors
    # ------------------------------------------------------------------

    def _select_character(self, inp: dict[str, Any]) -> list[str]:
        """character list → matched canonicals, capped at max_select."""
        raw = inp.get("character", [])
        tokens: list[str] = [raw] if isinstance(raw, str) else list(raw)
        max_sel = _module_max_select("pain_character", default=2)

        selected: list[str] = []
        seen: set[str] = set()
        for tok in tokens:
            canonical = _CHARACTER_TO_CANONICAL.get(tok.strip().lower())
            if canonical and canonical not in seen:
                seen.add(canonical)
                selected.append(canonical)
                if len(selected) >= max_sel:
                    break
        return selected

    def _select_laterality(self, inp: dict[str, Any]) -> list[str]:
        """side scalar → slot value if present in accepted values."""
        side = str(inp.get("side", "")).strip().lower()
        if side in {"links", "rechts", "beidseits"}:
            return [side]
        return []

    def _select_aggravating_mechanical(self, inp: dict[str, Any]) -> list[str]:
        """Single aggravating_factor → mechanical canonical if matched."""
        val = str(inp.get("aggravating_factor", "")).strip().lower()
        canonical = _AGG_MECH_TO_CANONICAL.get(val)
        return [canonical] if canonical else []

    def _select_aggravating_general(self, inp: dict[str, Any]) -> list[str]:
        """Single aggravating_factor → general canonical if matched."""
        val = str(inp.get("aggravating_factor", "")).strip().lower()
        canonical = _AGG_GENERAL_TO_CANONICAL.get(val)
        return [canonical] if canonical else []

    def _select_relieving_passive(self, inp: dict[str, Any]) -> list[str]:
        """Single relieving_factor → passive canonical if matched."""
        val = str(inp.get("relieving_factor", "")).strip().lower()
        canonical = _REL_PASSIVE_TO_CANONICAL.get(val)
        return [canonical] if canonical else []

    def _select_relieving_therapy(self, inp: dict[str, Any]) -> list[str]:
        """Single relieving_factor → therapy canonical if matched."""
        val = str(inp.get("relieving_factor", "")).strip().lower()
        canonical = _REL_THERAPY_TO_CANONICAL.get(val)
        return [canonical] if canonical else []

    def _select_radiation(self, inp: dict[str, Any]) -> list[str]:
        """
        radiation bool/str → radiation_target canonical if truthy.

        Priority:
          1. normalized_input["radiation_target"] if present and valid
          2. radiation itself if it's a string matching a known target
          3. generic "radiation" marker if radiation is just True
        """
        radiation = inp.get("radiation")
        if not radiation:
            return []

        # Check for explicit radiation_target slot
        target = str(inp.get("radiation_target", "")).strip()
        if target in _RADIATION_TARGETS:
            return [target]

        # radiation value itself might be a target name
        if isinstance(radiation, str) and radiation in _RADIATION_TARGETS:
            return [radiation]

        # radiation=True with no specific target → generic marker
        return ["radiation"]

    def _select_functional(
        self,
        inp:        dict[str, Any],
        valid_ids:  frozenset[str],
        module_name: str,
    ) -> list[str]:
        """functional_limitations list → matched canonicals, capped at max_select."""
        raw = inp.get("functional_limitations", [])
        tokens: list[str] = [raw] if isinstance(raw, str) else list(raw)
        max_sel = _module_max_select(module_name, default=2)

        selected: list[str] = []
        seen: set[str] = set()
        for tok in tokens:
            tok_lower = tok.strip().lower()
            if tok_lower in valid_ids and tok_lower not in seen:
                seen.add(tok_lower)
                selected.append(tok_lower)
                if len(selected) >= max_sel:
                    break
        return selected

    def _select_associated_mapped(
        self,
        inp:         dict[str, Any],
        alias_map:   dict[str, str],
        module_name: str,
    ) -> list[str]:
        """
        associated_symptoms list → mapped canonicals via alias_map.
        Overlay modules: only fire if there is actual associated_symptom input.
        """
        raw = inp.get("associated_symptoms", [])
        tokens: list[str] = [raw] if isinstance(raw, str) else list(raw)
        if not tokens:
            return []

        max_sel = _module_max_select(module_name, default=2)
        selected: list[str] = []
        seen: set[str] = set()

        for tok in tokens:
            canonical = alias_map.get(tok.strip().lower())
            if canonical and canonical not in seen:
                seen.add(canonical)
                selected.append(canonical)
                if len(selected) >= max_sel:
                    break
        return selected


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _module_max_select(module_name: str, default: int = 2) -> int:
    """Read max_select from the module definition, fall back to default."""
    defn = get_module_definition(module_name)
    if defn is None:
        return default
    return int(defn.get("max_select", default))
