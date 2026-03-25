"""
input_normalizer.py
-------------------
Deterministic input normalization layer for the AI-Draft pipeline.

Normalizes raw input_data before it reaches BlockSelector, so that
the selector always receives canonical, consistent values.

Rules:
- trim whitespace, collapse multiple spaces
- lowercase matching for alias lookup
- explicit alias maps — no fuzzy logic, no AI, no inference
- umlaut variants handled via explicit alias entries
- unknown values are passed through unchanged (no silent errors)

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Alias maps  (key: normalized-lowercase input → value: canonical form)
# ---------------------------------------------------------------------------

_SIDE_ALIASES: dict[str, str] = {
    # rechts variants
    "rechts":        "rechts",
    "rechtsbetont":  "rechts",
    "rechts betont": "rechts",
    "re.":           "rechts",
    "r.":            "rechts",
    # links variants
    "links":         "links",
    "linksbetont":   "links",
    "links betont":  "links",
    "li.":           "links",
    "l.":            "links",
    # beidseits variants
    "beidseits":     "beidseits",
    "bds.":          "beidseits",
    "beids.":        "beidseits",
    "beidseitig":    "beidseits",
    "bilateral":     "beidseits",
}

_CHARACTER_ALIASES: dict[str, str] = {
    "ziehend":          "ziehend",
    "dumpf-ziehend":    "ziehend",
    "zieht":            "ziehend",
    "stechend":         "stechend",
    "teilweise stechend": "stechend",
    "sticht":           "stechend",
    "dumpf":            "dumpf",
    "dumpf-drückend":   "dumpf",
    "dumpf-drueckend":  "dumpf",
    "drückend":         "dumpf",
    "drueckend":        "dumpf",
    "brennend":         "brennend",
    "lasierend":        "lasierend",
    "krampfartig":      "krampfartig",
}

# Normalized to trigger_label substrings so selector substring check succeeds
_AGGRAVATING_ALIASES: dict[str, str] = {
    # sitzen
    "sitzen":              "langes Sitzen",
    "sitzdauer":           "langes Sitzen",
    "langes sitzen":       "langes Sitzen",
    "laengeres sitzen":    "langes Sitzen",
    # bildschirm
    "bildschirmarbeit":            "längere Bildschirmarbeit",
    "laengere bildschirmarbeit":   "längere Bildschirmarbeit",
    "längere bildschirmarbeit":    "längere Bildschirmarbeit",
    "lange bildschirmarbeit":      "längere Bildschirmarbeit",
    "laengere bildschirm":         "längere Bildschirmarbeit",
    "pc-arbeit":                   "längere Bildschirmarbeit",
    "pc arbeit":                   "längere Bildschirmarbeit",
    "computer":                    "längere Bildschirmarbeit",
    "monitor":                     "längere Bildschirmarbeit",
    # kaelte
    "kälte":               "Kälte",
    "kaelte":              "Kälte",
    "kälteexposition":     "Kälte",
    "kaelteexposition":    "Kälte",
    # stress
    "stress":              "Stress",
    "belastung":           "Belastung",
}

_RELIEVING_ALIASES: dict[str, str] = {
    "wärme":              "Wärme",
    "waerme":             "Wärme",
    "wärmeanwendung":     "Wärme",
    "waermeanwendung":    "Wärme",
    "wärmeapplikation":   "Wärme",
    "waermeapplikation":  "Wärme",
    "wärmflasche":        "Wärme",
    "warm":               "Wärme",
    "heat":               "Wärme",
    # massage
    "massage":            "Massage",
    "massagen":           "Massage",
    # bewegung
    "bewegung":           "Bewegung",
    "spazieren":          "Bewegung",
}

_FUNCTIONAL_ALIASES: dict[str, str] = {
    # sitting_tolerance
    "sitzen":             "sitting_tolerance",
    "sitzdauer":          "sitting_tolerance",
    "sitztoleranz":       "sitting_tolerance",
    "sitting_tolerance":  "sitting_tolerance",
    "sitting":            "sitting_tolerance",
    # walking_distance
    "gehen":              "walking_distance",
    "gehstrecke":         "walking_distance",
    "laufen":             "walking_distance",
    "walking_distance":   "walking_distance",
    "walking":            "walking_distance",
    # head_rotation
    "kopfrotation":       "head_rotation",
    "kopf rotation":      "head_rotation",
    "rotation kopf":      "head_rotation",
    "head_rotation":      "head_rotation",
    "hws rotation":       "head_rotation",
    "hws-rotation":       "head_rotation",
    "rotation":           "head_rotation",   # accepted only in functional context
}

# Delimiters used to split character and functional_limitations strings
_SPLIT_PATTERN = re.compile(r"[,;/|]+")


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class InputNormalizer:
    """
    Normalizes raw input_data dict before it enters DraftPipeline.

    Keys processed: side, character, aggravating_factor,
                    relieving_factor, functional_limitations.
    All other keys are passed through unchanged.
    """

    def normalize_input(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Return a new dict with normalized values.
        The original dict is not modified.
        """
        result = dict(input_data)

        if "side" in result and result["side"] is not None:
            result["side"] = self._normalize_scalar(result["side"], _SIDE_ALIASES)

        if "character" in result:
            result["character"] = self._normalize_tokens(result["character"], _CHARACTER_ALIASES)

        if "aggravating_factor" in result and result["aggravating_factor"] is not None:
            result["aggravating_factor"] = self._normalize_scalar(
                result["aggravating_factor"], _AGGRAVATING_ALIASES
            )

        if "relieving_factor" in result and result["relieving_factor"] is not None:
            result["relieving_factor"] = self._normalize_scalar(
                result["relieving_factor"], _RELIEVING_ALIASES
            )

        if "functional_limitations" in result:
            result["functional_limitations"] = self._normalize_tokens(
                result["functional_limitations"], _FUNCTIONAL_ALIASES
            )

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _clean(self, value: str) -> str:
        """Trim whitespace and collapse multiple spaces."""
        return re.sub(r"\s+", " ", value).strip()

    def _normalize_scalar(self, value: Any, alias_map: dict[str, str]) -> Any:
        """
        Normalize a single string value via alias map.
        Returns canonical form if found, original (cleaned) value otherwise.
        """
        if not isinstance(value, str):
            return value
        cleaned = self._clean(value)
        key = cleaned.lower()
        return alias_map.get(key, cleaned)

    def _normalize_tokens(self, value: Any, alias_map: dict[str, str]) -> list[str]:
        """
        Normalize a list (or delimited string) of tokens via alias map.

        - Accepts list[str] or str
        - Splits strings by comma, semicolon, slash, pipe
        - Normalizes each token individually
        - Drops empty results
        - Deduplicates while preserving order
        """
        if isinstance(value, str):
            raw_tokens = _SPLIT_PATTERN.split(value)
        elif isinstance(value, list):
            # Expand any string items that contain delimiters
            raw_tokens = []
            for item in value:
                if isinstance(item, str):
                    raw_tokens.extend(_SPLIT_PATTERN.split(item))
                else:
                    raw_tokens.append(str(item))
        else:
            return []

        seen:   set[str]  = set()
        result: list[str] = []
        for token in raw_tokens:
            cleaned = self._clean(token)
            if not cleaned:
                continue
            normalized = alias_map.get(cleaned.lower(), cleaned)
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)

        return result
