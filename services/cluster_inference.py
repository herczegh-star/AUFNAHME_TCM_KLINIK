"""
cluster_inference.py
--------------------
Deterministic keyword-to-cluster inference used by Summary Review
and Pilot-Composer continuation flow.

Does NOT use AI or fuzzy matching.
First keyword match wins (order in _KEYWORD_TO_CLUSTER is significant).
"""

from __future__ import annotations


# Ordered list of (keyword_lowercase, storage_key).
# First match wins. Keywords are checked as substrings of normalized input text.
_KEYWORD_TO_CLUSTER: list[tuple[str, str]] = [
    ("lws",                      "lws_syndrom_v1_1"),
    ("hws",                      "hws_syndrom_v1_0"),
    ("migräne",                  "migraene_v1_0"),
    ("migraene",                 "migraene_v1_0"),
    ("kopfschmerz",              "kopfschmerzen_v1_0"),
    ("tinnitus",                 "tinnitus_aurium_v1_0"),
    ("polyneuropathie",          "polyneuropathische_beschwerden_polyneuropathie_v1_0"),
    ("polyneuropath",            "polyneuropathische_beschwerden_polyneuropathie_v1_0"),
    ("fibromyalgie",             "fibromyalgie_ganzkoerperschmerzen_v1_0"),
    ("reizdarm",                 "reizdarm_funktionelle_verdauungsbeschwerden_v1_0"),
    ("post-covid",               "post_covid_syndrom_v1_0"),
    ("post covid",               "post_covid_syndrom_v1_0"),
    ("morbus crohn",             "ced_ibd_morbus_crohn_colitis_ulcerosa_v1_0"),
    ("colitis",                  "ced_ibd_morbus_crohn_colitis_ulcerosa_v1_0"),
    ("ced",                      "ced_ibd_morbus_crohn_colitis_ulcerosa_v1_0"),
    ("sinusitis",                "chronische_sinusitis_rhinosinusitis_v1_0"),
    ("rhinosinusitis",           "chronische_sinusitis_rhinosinusitis_v1_0"),
    ("urtikaria",                "chronische_spontane_urtikaria_angiooedem_v1_0"),
    ("angioödem",                "chronische_spontane_urtikaria_angiooedem_v1_0"),
    ("angiooedem",               "chronische_spontane_urtikaria_angiooedem_v1_0"),
    ("endometriose",             "endometriose_v1_0"),
    ("polyarthritis",            "entzuedlich_rheumatologische_gelenkbeschwerden_polyarthritis_v1_0"),
    ("rheumat",                  "entzuedlich_rheumatologische_gelenkbeschwerden_polyarthritis_v1_0"),
    ("arthrose",                 "gelenkbeschwerden_arthrose_v1_0"),
    ("interstitielle zystitis",  "interstitielle_zystitis_v1_0"),
    ("wechseljahr",              "klimakterisches_syndrom_wechseljahresbeschwerden_v1_0"),
    ("klimakter",                "klimakterisches_syndrom_wechseljahresbeschwerden_v1_0"),
    ("lichen ruber",             "lichen_ruber_planus_v1_0"),
    ("lipödem",                  "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("lipoedem",                 "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("lymphödem",                "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("lymphoedem",               "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("morbus menière",           "morbus_meniere_v1_0"),
    ("morbus meniere",           "morbus_meniere_v1_0"),
    ("menière",                  "morbus_meniere_v1_0"),
    ("meniere",                  "morbus_meniere_v1_0"),
    ("müdigkeits",               "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("muedigkeits",              "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("erschöpfung",              "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("erschoepfung",             "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("neurodermitis",            "neurodermitis_atopisches_ekzem_v1_0"),
    ("atopisch",                 "neurodermitis_atopisches_ekzem_v1_0"),
    ("post-zoster",              "post_zoster_neuralgie_v1_0"),
    ("post zoster",              "post_zoster_neuralgie_v1_0"),
    ("zoster",                   "post_zoster_neuralgie_v1_0"),
    ("psoriasis",                "psoriasis_v1_0"),
    ("schuppenflechte",          "psoriasis_v1_0"),
    ("trigeminus",               "trigeminus_neuralgie_v1_0"),
]


def infer_cluster(text: str | None, valid_keys: list[str]) -> str:
    """
    Return storage_key inferred from complaint text, or '' if no match.

    Normalizes input to lowercase, checks substrings.
    Only returns keys present in valid_keys (guard against stale data).
    """
    if not text:
        return ""
    normalized = text.strip().lower()
    for keyword, key in _KEYWORD_TO_CLUSTER:
        if keyword in normalized and key in valid_keys:
            return key
    return ""
