from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SymptomProfile:
    symptom_group: str = ""
    localisation: str = ""
    side_or_dominance: str = ""
    duration: str = ""
    progression: str = ""
    character: str = ""
    radiation: str = ""
    aggravating_factors: str = ""
    relieving_factors: str = ""
    associated_symptoms: str = ""
    functional_impairment: str = ""
    known_diagnosis_or_context: str = ""


# Keyword hints for detecting whether a topic is already in the template text.
_HINTS: dict[str, list[str]] = {
    "progression":         ["zunehm", "verschlechter", "progred", "schub", "fluktu", "intermitt"],
    "character":           ["ziehend", "stechend", "dumpf", "pochend", "brennend", "drückend", "krampf", "kolik"],
    "radiation":           ["ausstrahl", "ausstrahlend"],
    "aggravating_factors": ["verstärk", "verschlechter", "bei belast", "unter stress", "bei kält"],
    "relieving_factors":   ["linderung", "besser", "wärme", "ruhe", "schonung"],
    "side_or_dominance":   ["rechts", "links", "betont", "beidseits", "einseitig"],
    "associated_symptoms": ["begleit", "übelkeit", "kribbeln", "taubheit", "schlafstör"],
}

# Known slot placeholders in templates.
_SLOTS: dict[str, str] = {
    "[Gelenk]":    "localisation",
    "[Region]":    "localisation",
    "[Charakter]": "character",
    "[Dauer]":     "duration",
    "[Ausstrahlung]": "radiation",
    "[Seite]":     "side_or_dominance",
}


class TemplateFiller:

    def fill_template(self, template_text: str, profile: SymptomProfile) -> str:
        text = self._replace_known_slots(template_text, profile)
        text = self._append_enrichments(text, profile)
        text = self._cleanup_text(text)
        return text

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _replace_known_slots(self, text: str, profile: SymptomProfile) -> str:
        for slot, attr in _SLOTS.items():
            value = getattr(profile, attr, "")
            if value and slot in text:
                text = text.replace(slot, value)
        return text

    def _contains_semantic_hint(self, text: str, category: str) -> bool:
        keywords = _HINTS.get(category, [])
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def _append_if_missing(self, text: str, sentence: str) -> str:
        if not text.endswith(" "):
            text = text.rstrip()
            if not text.endswith("."):
                text += "."
            text += " "
        return text + sentence

    def _cleanup_text(self, text: str) -> str:
        import re
        text = re.sub(r"\.\.+", ".", text)
        text = re.sub(r"  +", " ", text)
        text = text.strip()
        return text

    def _append_enrichments(self, text: str, profile: SymptomProfile) -> str:
        if profile.progression:
            text = self._append_if_missing(
                text,
                f"Im Verlauf habe sich die Symptomatik {profile.progression}."
            )

        if profile.character:
            text = self._append_if_missing(
                text,
                f"Die Schmerzen werden als {profile.character} beschrieben."
            )

        if profile.radiation:
            text = self._append_if_missing(
                text,
                f"Teilweise besteht eine Ausstrahlung {profile.radiation}."
            )

        if profile.side_or_dominance:
            text = self._append_if_missing(
                text,
                f"Die Beschwerden sind {profile.side_or_dominance}."
            )

        if profile.aggravating_factors:
            text = self._append_if_missing(
                text,
                f"Eine Verschlechterung tritt insbesondere {profile.aggravating_factors} auf."
            )

        if profile.relieving_factors:
            relief = profile.relieving_factors.lstrip()
            if relief.lower().startswith("durch "):
                relief = relief[6:]
            text = self._append_if_missing(
                text,
                f"Linderung erfolgt durch {relief}."
            )

        if profile.associated_symptoms:
            text = self._append_if_missing(
                text,
                f"Begleitend bestehen {profile.associated_symptoms}."
            )

        return text


# ------------------------------------------------------------------
# Usage example
# ------------------------------------------------------------------
#
# template_text = (
#     "Die Patientin berichtet seit vielen Jahren über intermittierend "
#     "auftretende Schmerzen im LWS-Bereich."
# )
#
# profile = SymptomProfile(
#     symptom_group="LWS-Syndrom",
#     duration="seit 5 Jahren",
#     progression="in den letzten 2 Jahren deutlich verschlechtert",
#     character="stechend und pochend",
#     radiation="in das linke Bein",
#     side_or_dominance="linksbetont",
#     aggravating_factors="bei Belastung",
#     relieving_factors="durch Wärme",
# )
#
# filler = TemplateFiller()
# result = filler.fill_template(template_text, profile)
# print(result)
#
# Expected output (style):
# "Die Patientin berichtet seit vielen Jahren über intermittierend auftretende
#  Schmerzen im LWS-Bereich. Im Verlauf habe sich die Symptomatik in den letzten
#  2 Jahren deutlich verschlechtert. Die Schmerzen werden als stechend und pochend
#  beschrieben. Teilweise besteht eine Ausstrahlung in das linke Bein. Die Beschwerden
#  sind linksbetont betont. Eine Verschlechterung tritt insbesondere bei Belastung auf.
#  Linderung erfolgt durch durch Wärme."
