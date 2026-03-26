"""
lexicons.py
-----------
Clinical German lexicons for the deterministic mining layer.

Lexicons are plain dicts: surface_form → canonical_value.
All surface forms are lowercase (matching is case-insensitive).

These are deliberately broad — the rule_patterns layer adds
context constraints on top of these raw token lists.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Cluster surface forms
# ---------------------------------------------------------------------------

CLUSTER_LEXICON: dict[str, str] = {
    # LWS
    "lws":                    "LWS-Syndrom",
    "lws-syndrom":            "LWS-Syndrom",
    "lendenwirbelsäule":      "LWS-Syndrom",
    "lendenwirbelsaeule":     "LWS-Syndrom",
    "lws-beschwerden":        "LWS-Syndrom",
    "kreuzschmerzen":         "LWS-Syndrom",
    "kreuzschmerz":           "LWS-Syndrom",
    "rückenschmerzen":        "LWS-Syndrom",
    "rueckenschmerzen":       "LWS-Syndrom",
    "rückenschmerz":          "LWS-Syndrom",
    "lumbago":                "LWS-Syndrom",
    "lumbalgie":              "LWS-Syndrom",

    # HWS
    "hws":                    "HWS-Syndrom",
    "hws-syndrom":            "HWS-Syndrom",
    "halswirbelsäule":        "HWS-Syndrom",
    "halswirbelsaeule":       "HWS-Syndrom",
    "hws-beschwerden":        "HWS-Syndrom",
    "nackenschmerzen":        "HWS-Syndrom",
    "nackenschmerz":          "HWS-Syndrom",
    "cervikalsyndrom":        "HWS-Syndrom",
    "zervikalsyndrom":        "HWS-Syndrom",
    "zervikale beschwerden":  "HWS-Syndrom",

    # Knie
    "knie":                   "Knie-Syndrom",
    "knieschmerzen":          "Knie-Syndrom",
    "knieschmerz":            "Knie-Syndrom",
    "gonarthrose":            "Knie-Syndrom",
    "kniegelenk":             "Knie-Syndrom",

    # Schulter
    "schulter":               "Schulter-Syndrom",
    "schulterprobleme":       "Schulter-Syndrom",
    "schultergelenk":         "Schulter-Syndrom",
    "periarthritis":          "Schulter-Syndrom",
    "rotatorenmanschette":    "Schulter-Syndrom",
}


# ---------------------------------------------------------------------------
# Side (laterality)
# ---------------------------------------------------------------------------

SIDE_LEXICON: dict[str, str] = {
    "beidseits":     "beidseits",
    "beidseitig":    "beidseits",
    "bilateral":     "beidseits",
    "bds.":          "beidseits",
    "beids.":        "beidseits",
    "rechts":        "rechts",
    "rechtsbetont":  "rechts",
    "re.":           "rechts",
    "links":         "links",
    "linksbetont":   "links",
    "li.":           "links",
}


# ---------------------------------------------------------------------------
# Pain character
# ---------------------------------------------------------------------------

CHARACTER_LEXICON: dict[str, str] = {
    "ziehend":           "ziehend",
    "dumpf-ziehend":     "ziehend",
    "zieht":             "ziehend",
    "stechend":          "stechend",
    "sticht":            "stechend",
    "einschießend":      "stechend",
    "dumpf":             "dumpf",
    "dumpf-drückend":    "dumpf",
    "drückend":          "dumpf",
    "drückt":            "dumpf",
    "brennend":          "brennend",
    "brennt":            "brennend",
    "krampfartig":       "krampfartig",
    "krampfend":         "krampfartig",
    "krampartig":        "krampfartig",
    "lasierend":         "lasierend",
    "bohrend":           "bohrend",
    "pulsierend":        "pulsierend",
    "elektrisierend":    "elektrisierend",
    "ausstrahlend":      "ausstrahlend",
}


# ---------------------------------------------------------------------------
# Aggravating factors
# ---------------------------------------------------------------------------

AGGRAVATING_LEXICON: dict[str, str] = {
    "langes sitzen":            "langes Sitzen",
    "längeres sitzen":          "langes Sitzen",
    "laengeres sitzen":         "langes Sitzen",
    "sitzen":                   "langes Sitzen",
    "sitzdauer":                "langes Sitzen",
    "bildschirmarbeit":         "längere Bildschirmarbeit",
    "bildschirm":               "längere Bildschirmarbeit",
    "pc-arbeit":                "längere Bildschirmarbeit",
    "pc arbeit":                "längere Bildschirmarbeit",
    "computer":                 "längere Bildschirmarbeit",
    "kälte":                    "Kälte",
    "kaelte":                   "Kälte",
    "kälteexposition":          "Kälte",
    "kalte umgebung":           "Kälte",
    "stress":                   "Stress",
    "belastung":                "Belastung",
    "körperliche belastung":    "Belastung",
    "bewegung":                 "Bewegung",
    "gehen":                    "langes Gehen",
    "langes stehen":            "langes Stehen",
    "stehen":                   "langes Stehen",
    "treppensteigen":           "Treppensteigen",
    "treppen":                  "Treppensteigen",
}


# ---------------------------------------------------------------------------
# Relieving factors
# ---------------------------------------------------------------------------

RELIEVING_LEXICON: dict[str, str] = {
    "wärme":              "Wärme",
    "waerme":             "Wärme",
    "wärmeanwendung":     "Wärme",
    "waermeanwendung":    "Wärme",
    "wärmflasche":        "Wärme",
    "wärmeapplikation":   "Wärme",
    "wärmebehandlung":    "Wärme",
    "warm":               "Wärme",
    "massage":            "Massage",
    "massagen":           "Massage",
    "massagebehandlung":  "Massage",
    "ruhe":               "Ruhe",
    "liegen":             "Liegen",
    "hinlegen":           "Liegen",
    "bewegung":           "Bewegung",
    "spazieren":          "Bewegung",
    "spaziergang":        "Bewegung",
    "dehnen":             "Dehnung",
    "dehnung":            "Dehnung",
    "stretching":         "Dehnung",
}


# ---------------------------------------------------------------------------
# Radiation targets
# ---------------------------------------------------------------------------

RADIATION_LEXICON: dict[str, str] = {
    "ausstrahlung":         "Ausstrahlung",
    "ausstrahlend":         "Ausstrahlung",
    "strahlt aus":          "Ausstrahlung",
    "strahlt":              "Ausstrahlung",
    "ins bein":             "Bein",
    "in das bein":          "Bein",
    "beinschmerzen":        "Bein",
    "oberschenkel":         "Oberschenkel",
    "unterschenkel":        "Unterschenkel",
    "fuß":                  "Fuß",
    "fuss":                 "Fuß",
    "gesäß":                "Gesäß",
    "gesaess":              "Gesäß",
    "in die schulter":      "Schulter",
    "in den arm":           "Arm",
    "arm":                  "Arm",
    "finger":               "Finger",
    "hand":                 "Hand",
    "kopf":                 "Kopf",
    "hinterkopf":           "Hinterkopf",
    "nacken":               "Nacken",
}


# ---------------------------------------------------------------------------
# Functional limitations
# ---------------------------------------------------------------------------

FUNCTIONAL_LEXICON: dict[str, str] = {
    "sitzen":               "sitting_tolerance",
    "sitztoleranz":         "sitting_tolerance",
    "sitzdauer":            "sitting_tolerance",
    "sitzt":                "sitting_tolerance",
    "gehen":                "walking_distance",
    "gehstrecke":           "walking_distance",
    "laufen":               "walking_distance",
    "kopfrotation":         "head_rotation",
    "rotation":             "head_rotation",
    "kopf drehen":          "head_rotation",
    "kopf dreht":           "head_rotation",
    "schlucken":            "swallowing",
    "schluckbeschwerden":   "swallowing",
    "treppensteigen":       "stair_climbing",
    "treppen":              "stair_climbing",
    "bücken":               "bending",
    "beugen":               "bending",
    "heben":                "lifting",
    "schlafen":             "sleep_quality",
    "schlafstörung":        "sleep_quality",
    "schlafqualität":       "sleep_quality",
}


# ---------------------------------------------------------------------------
# Associated symptoms
# ---------------------------------------------------------------------------

ASSOCIATED_LEXICON: dict[str, str] = {
    "morgensteifigkeit":       "morning_stiffness",
    "morgensteife":            "morning_stiffness",
    "steifigkeit":             "morning_stiffness",
    "kopfschmerzen":           "kopfschmerzen",
    "kopfschmerz":             "kopfschmerzen",
    "migräne":                 "kopfschmerzen",
    "schwindel":               "schwindel",
    "schwindelgefühl":         "schwindel",
    "tinnitus":                "tinnitus",
    "ohrgeräusche":            "tinnitus",
    "kribbeln":                "kribbeln",
    "kribbelgefühl":           "kribbeln",
    "parästhesien":            "kribbeln",
    "taubheitsgefühl":         "taubheit",
    "taubheit":                "taubheit",
    "schwäche":                "schwäche",
    "kraftlosigkeit":          "schwäche",
    "erschöpfung":             "erschöpfung",
    "müdigkeit":               "erschöpfung",
    "übelkeit":                "übelkeit",
    "nausea":                  "übelkeit",
}
