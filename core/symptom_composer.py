"""
symptom_composer.py
-------------------
Composes a final clinical German symptom paragraph from:
- a selected cluster text (anchor, pre-written template, or variant anchor)
- structured form data (primary source of truth)

Three cluster modes, three composition paths:

  structured  → slot-driven composition from form_data
                anchor = first sentence of generated cluster anchor
                primary if filled >= 3, fallback otherwise

  template    → pre-written clinical template is the base
                replace [dauer], [lokalisation] from form_data
                remove unresolved [placeholder] tokens cleanly
                append any missing slot info not already covered
                NEVER reduce to anchor + generic sentences

  variant     → select best variant anchor based on form_data content
                (currently: Müdigkeit chronisch vs. Post-Covid)
                then slot-driven composition from that anchor
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Variant mode config
# ---------------------------------------------------------------------------

_POSTCOVID_KEYWORDS = {"covid", "post-covid", "postcovid", "long covid", "postcovid-syndrom"}

_VARIANT_ANCHORS: dict[str, dict[str, str]] = {
    "Müdigkeit": {
        "default":  "Der Patient berichtet seit vielen Jahren über chronische Erschöpfung "
                    "und ausgeprägte Müdigkeit mit deutlich reduzierter Belastbarkeit.",
        "postcovid": "Der Patient berichtet über Beschwerden im Sinne eines Post-Covid-Syndroms "
                     "mit ausgeprägter Fatigue, reduzierter Belastbarkeit und Post-Exertional Malaise.",
    },
}


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

_HAS_PLACEHOLDER = re.compile(r"\[[a-z_äöü]+\]", re.IGNORECASE)


def _is_template_mode(text: str) -> bool:
    """Template mode texts contain [placeholder] tokens."""
    return bool(_HAS_PLACEHOLDER.search(text))


def _is_variant_mode(symptom_group: str) -> bool:
    return symptom_group in _VARIANT_ANCHORS


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
        template_text:  Cluster.text — pre-written template (template mode),
                        generated anchor (structured/variant mode).
        form_data:      Dict with keys: dauer, verlauf, charakter, seite,
                        ausstrahlung, verschlechterung, linderung, begleitsymptome
        symptom_group:  Cluster name, e.g. "LWS-Syndrom", "Müdigkeit".

    Returns:
        One compact clinical paragraph in German.
    """
    slots = _extract_slots(form_data)

    # --- PATH A: template mode ---
    if _is_template_mode(template_text):
        return _compose_template_mode(template_text, slots)

    # --- PATH B: variant mode ---
    if _is_variant_mode(symptom_group):
        return _compose_variant_mode(template_text, slots, symptom_group, form_data)

    # --- PATH C: structured mode ---
    return _compose_structured_mode(template_text, slots)


# ---------------------------------------------------------------------------
# Composition: template mode
# ---------------------------------------------------------------------------

def _compose_template_mode(template_text: str, slots: dict[str, str]) -> str:
    """
    For mode=template clusters:
    - pre-written template is the clinical base
    - replace [dauer] and [lokalisation] from slots
    - remove any remaining [placeholder] tokens cleanly
    - append missing slot information not already in the template
    """
    text = _replace_placeholders(template_text, slots)
    text = _remove_unresolved_placeholders(text)

    # Replace generic duration if dauer slot is filled
    if slots["dauer"]:
        text = re.sub(
            r"seit\s+(vielen|mehreren|einigen|langen)\s+Jahren",
            slots["dauer"],
            text,
            flags=re.IGNORECASE,
        )

    return _compose_fallback(text, slots)


# ---------------------------------------------------------------------------
# Composition: variant mode
# ---------------------------------------------------------------------------

def _compose_variant_mode(
    template_text: str,
    slots: dict[str, str],
    symptom_group: str,
    raw_form: dict[str, str],
) -> str:
    """
    For mode=variant clusters (currently: Müdigkeit):
    - select the right variant anchor based on form_data content
    - apply duration replacement
    - slot-driven composition from selected anchor
    """
    anchors = _VARIANT_ANCHORS[symptom_group]

    # Detect Post-Covid variant
    all_values = " ".join(raw_form.values()).lower()
    if any(kw in all_values for kw in _POSTCOVID_KEYWORDS):
        anchor = anchors["postcovid"]
    else:
        anchor = anchors["default"]

    # Replace generic duration in anchor
    if slots["dauer"]:
        anchor = re.sub(
            r"seit\s+(vielen|mehreren|einigen|langen)\s+Jahren",
            slots["dauer"],
            anchor,
            flags=re.IGNORECASE,
        )

    filled = sum(1 for v in slots.values() if v)
    if filled >= 2:
        return _compose_from_slots(anchor, slots, symptom_group)
    return _compose_fallback(anchor, slots)


# ---------------------------------------------------------------------------
# Composition: structured mode
# ---------------------------------------------------------------------------

def _compose_structured_mode(template_text: str, slots: dict[str, str]) -> str:
    """
    For mode=structured clusters:
    - replace generic duration in anchor
    - slot-driven if >= 3 fields filled, fallback otherwise
    """
    if slots["dauer"]:
        template_text = re.sub(
            r"seit\s+(vielen|mehreren|einigen|langen)\s+Jahren",
            slots["dauer"],
            template_text,
            flags=re.IGNORECASE,
        )

    anchor = _extract_anchor(template_text)
    filled = sum(1 for v in slots.values() if v)

    if filled >= 3:
        return _compose_from_slots(anchor, slots, "")
    return _compose_fallback(template_text, slots)


# ---------------------------------------------------------------------------
# Placeholder replacement (for template mode)
# ---------------------------------------------------------------------------

def _replace_placeholders(text: str, slots: dict[str, str]) -> str:
    """
    Replace known [placeholder] tokens from form slots.

    [dauer]      → slot value with leading "seit" stripped
                   (template already has "Seit" before the placeholder)
    [lokalisation] → NOT replaced from seite/laterality — left for cleanup
    [diagnose]   → pre-filled in Cluster.text; should not reach here
    """
    def replace(m: re.Match) -> str:
        key = m.group(1).lower()

        if key == "dauer" and slots["dauer"]:
            # Strip leading "seit " — template writes "Seit [dauer] bestehende..."
            return re.sub(r"^seit\s+", "", slots["dauer"], flags=re.IGNORECASE)

        # [lokalisation] must NOT be blindly mapped to laterality (seite field).
        # A Polyneuropathie template expects a body region ("an den Beinen"),
        # not "linksbetont". Leave unresolved; _remove_unresolved_placeholders handles it.

        return m.group(0)  # leave unknown placeholders for cleanup

    return re.sub(r"\[([^\]]+)\]", replace, text)


def _remove_unresolved_placeholders(text: str) -> str:
    """
    Remove [placeholder] tokens that were not replaced.
    Handles common grammatical contexts to avoid malformed sentences.

    Examples:
      "...aufsteigend bis [lokalisation]."  →  "...aufsteigend."
      "...im Rahmen einer [diagnose]."      →  "...im Rahmen einer bekannten Erkrankung."
      "...in [lokalisation] sowie..."       →  "...sowie..."
    """
    # Prepositions/articles directly before [placeholder]
    text = re.sub(
        r"\s+(bis|in|nach|an|im|eines|einer|einem|einen|von|bei)\s+\[[^\]]+\]",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Any remaining [placeholder] tokens
    text = re.sub(r"\s*\[[^\]]+\]", "", text)
    return _cleanup(text)


# ---------------------------------------------------------------------------
# Slot extraction and normalization
# ---------------------------------------------------------------------------

def _extract_slots(form_data: dict[str, str]) -> dict[str, str]:
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
    sentences = re.split(r"(?<=\.)\s+", template_text.strip())
    return sentences[0].strip() if sentences else template_text.strip()


# ---------------------------------------------------------------------------
# Composition strategies (shared by structured and variant paths)
# ---------------------------------------------------------------------------

def _compose_from_slots(
    anchor: str,
    slots: dict[str, str],
    symptom_group: str,
) -> str:
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
        parts.append(f"Eine Verschlechterung tritt insbesondere {slots['verschlechterung']} auf.")

    if slots["linderung"]:
        parts.append(f"Linderung erfolgt durch {slots['linderung']}.")

    if slots["begleitsymptome"]:
        parts.append(f"Begleitend besteht {slots['begleitsymptome']}.")

    return _join_sentences(parts)


def _compose_fallback(text: str, slots: dict[str, str]) -> str:
    """
    Keep the base text and selectively append slots not already covered.
    Used for template mode (base = full pre-written template) and
    structured mode with few filled fields (base = full anchor text).
    """
    text = text.strip()
    text_lower = text.lower()

    def already_covered(keywords: list[str]) -> bool:
        return any(kw in text_lower for kw in keywords)

    if slots["verlauf"] and not already_covered(["verschlechtert", "progred", "zunehm", "schub", "fluktu", "intermit"]):
        text = _append(text, f"Im Verlauf habe sich die Symptomatik {slots['verlauf']}.")

    if slots["charakter"] and not already_covered(["ziehend", "stechend", "dumpf", "pochend", "brennend", "drückend", "parästhesien", "kribbeln"]):
        text = _append(text, f"Die Beschwerden werden als {slots['charakter']} beschrieben.")

    if slots["ausstrahlung"] and not already_covered(["ausstrahl"]):
        text = _append(text, f"Teilweise besteht eine Ausstrahlung {slots['ausstrahlung']}.")

    if slots["seite"] and not already_covered(["rechts", "links", "betont", "beidseits", "einseitig"]):
        text = _append(text, f"Die Beschwerden sind {slots['seite']}.")

    if slots["verschlechterung"] and not already_covered(["verstärk", "verschlechter", "belastung", "stress"]):
        text = _append(text, f"Eine Verschlechterung tritt insbesondere {slots['verschlechterung']} auf.")

    if slots["linderung"] and not already_covered(["linderung", "wärme", "ruhe", "massage", "manuelle therapie"]):
        text = _append(text, f"Linderung erfolgt durch {slots['linderung']}.")

    if slots["begleitsymptome"] and not already_covered(["begleit", "kribbeln", "taubheit", "übelkeit", "schwindel"]):
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
    # Fix double commas or trailing comma before period
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\s+\.", ".", text)
    return text.strip()
