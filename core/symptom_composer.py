"""
symptom_composer.py
-------------------
Composes a final clinical German symptom paragraph from:
- a selected cluster text (framing anchor or pre-written template)
- structured form data (primary source of truth)

Architecture:
    1. Replace [placeholder] slots in template texts from form_data
    2. Normalize raw form values (fix wording, add prepositions)
    3. Detect how many slots are filled → decide composition strategy
    4. If enough slots filled: build paragraph from form data, using
       only the first sentence of the template as introductory anchor
    5. If few slots filled: fall back to template with selective appending
    6. Return one clean compact paragraph

Insertion point in project:
    ui/app.py → compose_symptom_text(t.text, form_data, group)
    where t is now a Cluster object from template_repository.py
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_symptom_text(
    template_text: str,
    form_data: dict[str, str],
    symptom_group: str = "",
) -> str:
    """
    Compose a final clinical German paragraph.

    Args:
        template_text:  Cluster text — either a pre-written template
                        (mode=template, may contain [placeholders]) or
                        a generated anchor sentence (mode=structured/variant).
        form_data:      Dict with keys matching form fields (see below).
        symptom_group:  Symptom group string, e.g. 'LWS-Syndrom'.

    Recognised form_data keys:
        dauer, verlauf, charakter, seite, ausstrahlung,
        verschlechterung, linderung, begleitsymptome

    Returns:
        One compact clinical paragraph.
    """
    slots = _extract_slots(form_data)

    # Step 1: fill [placeholder] slots in template texts (mode=template)
    template_text = _replace_placeholders(template_text, slots)

    # Step 2: replace generic duration phrase if user provided dauer
    if slots["dauer"]:
        template_text = re.sub(
            r"seit\s+(vielen|mehreren|einigen|langen)\s+Jahren",
            slots["dauer"],
            template_text,
            flags=re.IGNORECASE,
        )
        # also handle "Seit [dauer]" placeholder pattern
        template_text = re.sub(
            r"Seit\s+\[dauer\]",
            f"Seit {slots['dauer'].removeprefix('seit ').removeprefix('Seit ')}",
            template_text,
            flags=re.IGNORECASE,
        )

    anchor = _extract_anchor(template_text)
    filled = sum(1 for v in slots.values() if v)

    if filled >= 3:
        return _compose_from_slots(anchor, slots, symptom_group)
    else:
        return _compose_fallback(template_text, slots)


# ---------------------------------------------------------------------------
# Placeholder replacement (for mode=template clusters)
# ---------------------------------------------------------------------------

_PLACEHOLDER_MAP = {
    "dauer":       "dauer",
    "lokalisation": "seite",
    "diagnose":    None,   # no direct form field, skip
}


def _replace_placeholders(text: str, slots: dict[str, str]) -> str:
    """
    Replace [placeholder] tokens in template texts with form_data values.

    Templates use the pattern:  "Seit [dauer] bestehende..."
    The slot value is "seit 3 Jahren" — so we strip the leading "seit"
    to avoid "Seit seit 3 Jahren".
    """
    def replace(m: re.Match) -> str:
        key = m.group(1).lower()
        if key == "dauer" and slots["dauer"]:
            # Strip leading "seit" — template already provides it
            val = re.sub(r"^seit\s+", "", slots["dauer"], flags=re.IGNORECASE)
            return val
        if key == "lokalisation" and slots["seite"]:
            return slots["seite"]
        if key == "diagnose":
            return m.group(0)  # keep as-is, LLM will handle context
        return m.group(0)

    return re.sub(r"\[([^\]]+)\]", replace, text)


# ---------------------------------------------------------------------------
# Slot extraction and normalization
# ---------------------------------------------------------------------------

def _extract_slots(form_data: dict[str, str]) -> dict[str, str]:
    """Normalize all form values into clean slot strings."""
    def get(key: str) -> str:
        return form_data.get(key, "").strip()

    return {
        "dauer":            _normalize_dauer(get("dauer")),
        "verlauf":          _normalize_generic(get("verlauf")),
        "charakter":        _normalize_charakter(get("charakter")),
        "seite":            _normalize_generic(get("seite")),
        "ausstrahlung":     _normalize_ausstrahlung(get("ausstrahlung")),
        "verschlechterung": _normalize_verschlechterung(get("verschlechterung")),
        "linderung":        _normalize_linderung(get("linderung")),
        "begleitsymptome":  _normalize_begleitsymptome(get("begleitsymptome")),
    }


def _normalize_dauer(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    if re.fullmatch(r"\d+", value):
        return f"seit {value} Jahren"
    if not value.lower().startswith("seit"):
        return f"seit {value}"
    return value


def _normalize_charakter(value: str) -> str:
    if not value:
        return ""
    replacements = [
        (r"\bstechen\b", "stechend"),
        (r"\bziehen\b", "ziehend"),
        (r"\bdrücken\b", "drückend"),
        (r"\bpochend\b", "pochend"),
        (r"\bbrennen\b", "brennend"),
        (r"\bdumpf\b", "dumpf"),
        (r"\bkrampf\b", "krampfartig"),
    ]
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return _normalize_generic(value)


def _normalize_ausstrahlung(value: str) -> str:
    if not value:
        return ""
    value = _normalize_generic(value)
    if not re.match(r"^(in|nach|bis)\b", value, re.IGNORECASE):
        value = f"in {value}"
    return value


def _normalize_verschlechterung(value: str) -> str:
    if not value:
        return ""
    value = _normalize_generic(value)
    value = re.sub(r"\blänger[e]?\s+Sitzen\b", "längerem Sitzen", value, flags=re.IGNORECASE)
    value = re.sub(r"\blang[e]?\s+Sitzen\b",   "längerem Sitzen", value, flags=re.IGNORECASE)
    value = re.sub(r"\bkälte\b", "Kälte", value, flags=re.IGNORECASE)
    return value


def _normalize_linderung(value: str) -> str:
    if not value:
        return ""
    value = _normalize_generic(value)
    value = re.sub(r"^durch\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bmanuell[e]?\s+[Tt]herapie[n]?\b", "manuelle Therapie", value)
    return value


def _normalize_begleitsymptome(value: str) -> str:
    if not value:
        return ""
    value = _normalize_generic(value)
    value = re.sub(
        r"\bKribbeln\s+(?:Zehen\s+)?(li|re)\s+Bein\b",
        lambda m: f"Kribbeln im {'linken' if m.group(1) == 'li' else 'rechten'} Bein",
        value,
    )
    value = re.sub(r"\bKribbeln\s+Zehen\b", "Kribbeln in den Zehen", value)
    return value


def _normalize_generic(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r",\s*,", ",", value)
    value = re.sub(r",([^\s])", r", \1", value)
    return value.strip()


# ---------------------------------------------------------------------------
# Anchor extraction
# ---------------------------------------------------------------------------

def _extract_anchor(template_text: str) -> str:
    """Return only the first sentence of the template as framing anchor."""
    sentences = re.split(r"(?<=\.)\s+", template_text.strip())
    if sentences:
        return sentences[0].strip()
    return template_text.strip()


# ---------------------------------------------------------------------------
# Composition strategies
# ---------------------------------------------------------------------------

def _compose_from_slots(
    anchor: str,
    slots: dict[str, str],
    symptom_group: str,
) -> str:
    """
    Primary strategy: build paragraph from form slots.
    Uses anchor sentence as opening, then slot-driven sentences.
    Works for all cluster types (LWS, HWS, Migräne, Tinnitus, etc.).
    """
    parts: list[str] = [anchor]

    if slots["verlauf"]:
        parts.append(f"Im Verlauf habe sich die Symptomatik {slots['verlauf']}.")

    if slots["charakter"]:
        parts.append(f"Die Beschwerden werden überwiegend als {slots['charakter']} beschrieben.")

    ausstrahlung = slots["ausstrahlung"]
    seite = slots["seite"]
    if ausstrahlung and seite:
        parts.append(f"Teilweise besteht eine Ausstrahlung {ausstrahlung}, {seite}.")
    elif ausstrahlung:
        parts.append(f"Teilweise besteht eine Ausstrahlung {ausstrahlung}.")
    elif seite:
        parts.append(f"Die Beschwerden sind {seite}.")

    if slots["verschlechterung"]:
        parts.append(
            f"Eine Verschlechterung tritt insbesondere {slots['verschlechterung']} auf."
        )

    if slots["linderung"]:
        parts.append(f"Linderung erfolgt durch {slots['linderung']}.")

    if slots["begleitsymptome"]:
        parts.append(f"Begleitend besteht {slots['begleitsymptome']}.")

    return _join_sentences(parts)


def _compose_fallback(template_text: str, slots: dict[str, str]) -> str:
    """
    Fallback strategy: keep full template, append only filled slots
    that are not already semantically covered.
    """
    text = template_text.strip()
    text_lower = text.lower()

    def already_covered(keywords: list[str]) -> bool:
        return any(kw in text_lower for kw in keywords)

    if slots["verlauf"] and not already_covered(["verschlechtert", "progred", "zunehm", "schub", "fluktu"]):
        text = _append(text, f"Im Verlauf habe sich die Symptomatik {slots['verlauf']}.")

    if slots["charakter"] and not already_covered(["ziehend", "stechend", "dumpf", "pochend", "brennend", "drückend"]):
        text = _append(text, f"Die Beschwerden werden als {slots['charakter']} beschrieben.")

    if slots["ausstrahlung"] and not already_covered(["ausstrahl"]):
        text = _append(text, f"Teilweise besteht eine Ausstrahlung {slots['ausstrahlung']}.")

    if slots["seite"] and not already_covered(["rechts", "links", "betont", "beidseits"]):
        text = _append(text, f"Die Beschwerden sind {slots['seite']}.")

    if slots["verschlechterung"] and not already_covered(["verstärk", "verschlechter"]):
        text = _append(text, f"Eine Verschlechterung tritt insbesondere {slots['verschlechterung']} auf.")

    if slots["linderung"] and not already_covered(["linderung", "wärme", "ruhe", "manuelle therapie"]):
        text = _append(text, f"Linderung erfolgt durch {slots['linderung']}.")

    if slots["begleitsymptome"] and not already_covered(["begleit", "kribbeln", "taubheit"]):
        text = _append(text, f"Begleitend besteht {slots['begleitsymptome']}.")

    return _cleanup(text)


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _append(text: str, sentence: str) -> str:
    text = text.rstrip()
    if not text.endswith("."):
        text += "."
    return text + " " + sentence


def _join_sentences(parts: list[str]) -> str:
    result = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if result:
            result = result.rstrip()
            if not result.endswith("."):
                result += "."
            result += " " + part
        else:
            result = part
    return _cleanup(result)


def _cleanup(text: str) -> str:
    text = re.sub(r"\.\.+", ".", text)
    text = re.sub(r"  +", " ", text)
    text = text.strip()
    return text
