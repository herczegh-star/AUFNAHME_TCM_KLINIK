"""
rule_patterns.py
----------------
Compiled regex patterns for deterministic candidate extraction.

Each RulePattern defines:
  - id:           unique identifier
  - pattern_type: semantic category (side, character, aggravating, ...)
  - cluster_hint: optional cluster association ("" = any cluster)
  - regex:        compiled pattern that captures the matched surface form
  - canonical:    the normalized output value for this match

Patterns are tested in order — first match per type per sentence wins
(unless multi=True, then all matches are collected).

Design:
  - Word boundaries wherever possible to avoid false positives
  - Case-insensitive matching throughout
  - No lookahead/lookbehind unless strictly necessary for precision
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Pattern model
# ---------------------------------------------------------------------------

@dataclass
class RulePattern:
    id:           str
    pattern_type: str
    canonical:    str
    regex:        re.Pattern[str]
    cluster_hint: str  = ""
    multi:        bool = False   # if True: collect all non-overlapping matches


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(
    pid:          str,
    ptype:        str,
    canonical:    str,
    pattern:      str,
    cluster_hint: str  = "",
    multi:        bool = False,
) -> RulePattern:
    return RulePattern(
        id           = pid,
        pattern_type = ptype,
        canonical    = canonical,
        regex        = re.compile(pattern, re.IGNORECASE),
        cluster_hint = cluster_hint,
        multi        = multi,
    )


# ---------------------------------------------------------------------------
# SIDE patterns
# ---------------------------------------------------------------------------

SIDE_PATTERNS: list[RulePattern] = [
    _p("side_beidseits",  "side", "beidseits",
       r"\b(beidseits|beidseitig|bilateral|bds\.?|beids\.?)\b"),
    _p("side_rechts",     "side", "rechts",
       r"\b(rechts(?:betont)?|rechtsseitig|re\.)\b"),
    _p("side_links",      "side", "links",
       r"\b(links(?:betont)?|linksseitig|li\.)\b"),
]


# ---------------------------------------------------------------------------
# CHARACTER patterns
# ---------------------------------------------------------------------------

CHARACTER_PATTERNS: list[RulePattern] = [
    _p("char_ziehend",        "character", "ziehend",
       r"\b(ziehend(?:e[rns]?)?|dumpf-ziehend|zieht)\b", multi=True),
    _p("char_stechend",       "character", "stechend",
       r"\b(stechend(?:e[rns]?)?|einschieß(?:end)?|sticht)\b", multi=True),
    _p("char_dumpf",          "character", "dumpf",
       r"\b(dumpf(?:-drückend)?|drückend(?:e[rns]?)?|drückt)\b", multi=True),
    _p("char_brennend",       "character", "brennend",
       r"\b(brennend(?:e[rns]?)?|brennt)\b", multi=True),
    _p("char_krampfartig",    "character", "krampfartig",
       r"\b(krampfartig|krampfend|krampartig)\b", multi=True),
    _p("char_bohrend",        "character", "bohrend",
       r"\b(bohrend(?:e[rns]?)?)\b", multi=True),
    _p("char_pulsierend",     "character", "pulsierend",
       r"\b(pulsierend(?:e[rns]?)?)\b", multi=True),
    _p("char_lasierend",      "character", "lasierend",
       r"\b(lasierend(?:e[rns]?)?)\b", multi=True),
    _p("char_elektrisierend", "character", "elektrisierend",
       r"\b(elektrisierend(?:e[rns]?)?)\b", multi=True),
]


# ---------------------------------------------------------------------------
# RADIATION patterns
# ---------------------------------------------------------------------------

RADIATION_PATTERNS: list[RulePattern] = [
    _p("radiation_generic",  "radiation", "Ausstrahlung",
       r"\b(ausstrahlung|ausstrahlend|strahlt\s+(?:bis\s+)?(?:in|aus|nach))\b"),
    _p("radiation_bein",     "radiation", "Bein",
       r"\b(?:strahlt|ausstrahlung|ausstrahlend).{0,30}(?:ins?\s+bein|beinschmerz|unterschenkel|oberschenkel)\b",
       cluster_hint="LWS-Syndrom"),
    _p("radiation_gesaess",  "radiation", "Gesäß",
       r"\b(?:strahlt|ausstrahlung|ausstrahlend).{0,30}(?:ges[äa]ß|gesaess)\b",
       cluster_hint="LWS-Syndrom"),
    _p("radiation_arm",      "radiation", "Arm",
       r"\b(?:strahlt|ausstrahlung|ausstrahlend).{0,30}(?:in\s+den\s+arm|arm|finger|hand)\b",
       cluster_hint="HWS-Syndrom"),
    _p("radiation_kopf",     "radiation", "Kopf",
       r"\b(?:strahlt|ausstrahlung|ausstrahlend).{0,30}(?:kopf|hinterkopf|nacken)\b",
       cluster_hint="HWS-Syndrom"),
]


# ---------------------------------------------------------------------------
# AGGRAVATING FACTOR patterns
# ---------------------------------------------------------------------------

AGGRAVATING_PATTERNS: list[RulePattern] = [
    _p("agg_sitzen",       "aggravating", "langes Sitzen",
       r"\b(?:(?:langes?|l[äa]ngeres?)\s+)?sitz(?:en|dauer|toleranz|t)\b"),
    _p("agg_bildschirm",   "aggravating", "längere Bildschirmarbeit",
       r"\b(?:bildschirmarbeit|bildschirm|pc-?arbeit|computer(?:arbeit)?|monitor)\b"),
    _p("agg_kaelte",       "aggravating", "Kälte",
       r"\b(?:k[äa]lte(?:exposition)?|kalte?\s+(?:umgebung|witterung|luft|wetter))\b"),
    _p("agg_stress",       "aggravating", "Stress",
       r"\b(?:stress|psychische[rns]?\s+(?:belastung|stress))\b"),
    _p("agg_belastung",    "aggravating", "Belastung",
       r"\b(?:k[öo]rperliche[rns]?\s+belastung|sportliche[rns]?\s+belastung|anstrengung)\b"),
    _p("agg_stehen",       "aggravating", "langes Stehen",
       r"\b(?:(?:langes?|l[äa]ngeres?)\s+)?steh(?:en|dauer)\b"),
    _p("agg_treppensteigen", "aggravating", "Treppensteigen",
       r"\b(?:treppensteigen|treppen\s+steigen|treppengehen)\b"),
    _p("agg_gehen_lws",    "aggravating", "langes Gehen",
       r"\b(?:(?:langes?|l[äa]ngeres?)\s+)?geh(?:en|strecke)\b",
       cluster_hint="LWS-Syndrom"),
]


# ---------------------------------------------------------------------------
# RELIEVING FACTOR patterns
# ---------------------------------------------------------------------------

RELIEVING_PATTERNS: list[RulePattern] = [
    _p("rel_waerme",    "relieving", "Wärme",
       r"\b(?:w[äa]rme(?:anwendung|applikation|behandlung|flasche)?|warm(?:e[rns]?)?|heat)\b"),
    _p("rel_massage",   "relieving", "Massage",
       r"\b(?:massage(?:n|behandlung|therapie)?)\b"),
    _p("rel_ruhe",      "relieving", "Ruhe",
       r"\b(?:ruhe|ausruhen|ausruht)\b"),
    _p("rel_liegen",    "relieving", "Liegen",
       r"\b(?:liegen|hinlegen|h[äa]ngt|entspanntes?\s+liegen)\b"),
    _p("rel_bewegung",  "relieving", "Bewegung",
       r"\b(?:leichte[rns]?\s+bewegung|spazier(?:en|gang|gehen)|lockerung)\b"),
    _p("rel_dehnen",    "relieving", "Dehnung",
       r"\b(?:dehnen|dehnung|stretching|strecken)\b"),
]


# ---------------------------------------------------------------------------
# FUNCTIONAL LIMITATION patterns
# ---------------------------------------------------------------------------

FUNCTIONAL_PATTERNS: list[RulePattern] = [
    _p("func_sitz",    "functional", "sitting_tolerance",
       r"\b(?:sitztoleranz|sitzdauer|langes?\s+sitzen|sitzen\s+(?:nur|kaum|nicht|ist))\b",
       multi=True),
    _p("func_geh",     "functional", "walking_distance",
       r"\b(?:gehstrecke|gehf[äa]higkeit|langes?\s+gehen|laufen\s+(?:nur|kaum|nicht|ist))\b",
       multi=True),
    _p("func_rotation", "functional", "head_rotation",
       r"\b(?:kopfrotation|kopf\s+dreh(?:en|t)|rotation\s+(?:des?\s+)?(?:kopf|hws))\b",
       cluster_hint="HWS-Syndrom", multi=True),
    _p("func_schlaf",  "functional", "sleep_quality",
       r"\b(?:schlafst[öo]rung(?:en)?|schlafqualit[äa]t|schlafen\s+(?:schwierig|schlecht))\b",
       multi=True),
    _p("func_heben",   "functional", "lifting",
       r"\b(?:schweres?\s+heben|heben\s+(?:schwer|nicht|kaum|ist))\b",
       multi=True),
    _p("func_buecken", "functional", "bending",
       r"\b(?:b[üu]cken|vornebeugen|beugen\s+(?:nicht|kaum|ist))\b",
       multi=True),
]


# ---------------------------------------------------------------------------
# ASSOCIATED SYMPTOM patterns
# ---------------------------------------------------------------------------

ASSOCIATED_PATTERNS: list[RulePattern] = [
    _p("assoc_morgensteif",  "associated", "morning_stiffness",
       r"\b(?:morgensteifigkeit|morgensteife|steifigkeit\s+morgen(?:s)?)\b"),
    _p("assoc_kopfschmerzen", "associated", "kopfschmerzen",
       r"\b(?:kopfschmerzen?|migr[äa]ne)\b",
       cluster_hint="HWS-Syndrom"),
    _p("assoc_schwindel",    "associated", "schwindel",
       r"\b(?:schwindel(?:gefühl)?|drehschwindel)\b"),
    _p("assoc_tinnitus",     "associated", "tinnitus",
       r"\b(?:tinnitus|ohrger[äa]usche?|ohrensausen)\b"),
    _p("assoc_kribbeln",     "associated", "kribbeln",
       r"\b(?:kribbeln|kribbelgef[üu]hl|par[äa]sthesien?)\b"),
    _p("assoc_taubheit",     "associated", "taubheit",
       r"\b(?:taubheitsgef[üu]hl|taubheit|taubes?\s+gef[üu]hl)\b"),
    _p("assoc_erschoepfung", "associated", "erschöpfung",
       r"\b(?:erschöpfung|erschöpft|m[üu]digkeit|m[üu]de)\b"),
    _p("assoc_schwaeche",    "associated", "schwäche",
       r"\b(?:schw[äa]che|kraftlosigkeit|kraft(?:verlust)?)\b"),
]


# ---------------------------------------------------------------------------
# CLUSTER patterns (for cluster detection in Diagnosen / whole-doc scan)
# ---------------------------------------------------------------------------

CLUSTER_PATTERNS: list[RulePattern] = [
    _p("cluster_lws",    "cluster", "LWS-Syndrom",
       r"\b(?:lws(?:-syndrom)?|lendenwirbels[äa]ule|kreuzschmerzen?|lumbago|lumbalgie|r[üu]ckenschmerzen?)\b"),
    _p("cluster_hws",    "cluster", "HWS-Syndrom",
       r"\b(?:hws(?:-syndrom)?|halswirbels[äa]ule|nackenschmerzen?|[cz]ervikal(?:syndrom)?)\b"),
    _p("cluster_knie",   "cluster", "Knie-Syndrom",
       r"\b(?:knie(?:schmerzen?|gelenk)?|gonarthrose)\b"),
    _p("cluster_schulter", "cluster", "Schulter-Syndrom",
       r"\b(?:schulter(?:gelenk|schmerzen?|probleme)?|periarthritis|rotatorenmanschette)\b"),
]


# ---------------------------------------------------------------------------
# All patterns combined (for convenience iteration)
# ---------------------------------------------------------------------------

ALL_PATTERNS: list[RulePattern] = (
    SIDE_PATTERNS
    + CHARACTER_PATTERNS
    + RADIATION_PATTERNS
    + AGGRAVATING_PATTERNS
    + RELIEVING_PATTERNS
    + FUNCTIONAL_PATTERNS
    + ASSOCIATED_PATTERNS
    + CLUSTER_PATTERNS
)
