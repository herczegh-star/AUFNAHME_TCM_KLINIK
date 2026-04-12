"""
screen_summary_review.py
------------------------
Screen 2b — Summary review step between interview and composer.

Physician can inspect and edit the collected interview answers
and select the cluster to open in Pilot-Composer before proceeding.

No AI. No automatic cluster matching.
"""

from __future__ import annotations

import flet as ft

from models.case_summary import CaseSummary
from services.unified_cluster_service import list_available_with_names
from ui.theme import _C_ACCENT, _C_TEXT_SECONDARY


_FIELDS = [
    ("Hauptbeschwerde",                             "most_burdensome"),
    ("Weitere im Vordergrund stehende Beschwerden", "priority_complaint"),
    ("Weitere Beschwerden",                         "additional_complaints"),
]

# Ordered list of (keyword_lowercase, storage_key).
# First match wins. Keywords are checked as substrings of normalized Hauptbeschwerde.
_KEYWORD_TO_CLUSTER: list[tuple[str, str]] = [
    ("lws",                 "lws_syndrom_v1_1"),
    ("hws",                 "hws_syndrom_v1_0"),
    ("migräne",             "migraene_v1_0"),
    ("migraene",            "migraene_v1_0"),
    ("kopfschmerz",         "kopfschmerzen_v1_0"),
    ("tinnitus",            "tinnitus_aurium_v1_0"),
    ("polyneuropathie",     "polyneuropathische_beschwerden_polyneuropathie_v1_0"),
    ("polyneuropath",       "polyneuropathische_beschwerden_polyneuropathie_v1_0"),
    ("fibromyalgie",        "fibromyalgie_ganzkoerperschmerzen_v1_0"),
    ("reizdarm",            "reizdarm_funktionelle_verdauungsbeschwerden_v1_0"),
    ("post-covid",          "post_covid_syndrom_v1_0"),
    ("post covid",          "post_covid_syndrom_v1_0"),
    ("morbus crohn",        "ced_ibd_morbus_crohn_colitis_ulcerosa_v1_0"),
    ("colitis",             "ced_ibd_morbus_crohn_colitis_ulcerosa_v1_0"),
    ("ced",                 "ced_ibd_morbus_crohn_colitis_ulcerosa_v1_0"),
    ("sinusitis",           "chronische_sinusitis_rhinosinusitis_v1_0"),
    ("rhinosinusitis",      "chronische_sinusitis_rhinosinusitis_v1_0"),
    ("urtikaria",           "chronische_spontane_urtikaria_angiooedem_v1_0"),
    ("angioödem",           "chronische_spontane_urtikaria_angiooedem_v1_0"),
    ("angiooedem",          "chronische_spontane_urtikaria_angiooedem_v1_0"),
    ("endometriose",        "endometriose_v1_0"),
    ("polyarthritis",       "entzuedlich_rheumatologische_gelenkbeschwerden_polyarthritis_v1_0"),
    ("rheumat",             "entzuedlich_rheumatologische_gelenkbeschwerden_polyarthritis_v1_0"),
    ("arthrose",            "gelenkbeschwerden_arthrose_v1_0"),
    ("interstitielle zystitis", "interstitielle_zystitis_v1_0"),
    ("wechseljahr",         "klimakterisches_syndrom_wechseljahresbeschwerden_v1_0"),
    ("klimakter",           "klimakterisches_syndrom_wechseljahresbeschwerden_v1_0"),
    ("lichen ruber",        "lichen_ruber_planus_v1_0"),
    ("lipödem",             "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("lipoedem",            "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("lymphödem",           "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("lymphoedem",          "lipooedem_lymphoedem_lip_lymphoedem_v1_0"),
    ("morbus menière",      "morbus_meniere_v1_0"),
    ("morbus meniere",      "morbus_meniere_v1_0"),
    ("menière",             "morbus_meniere_v1_0"),
    ("meniere",             "morbus_meniere_v1_0"),
    ("müdigkeits",          "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("muedigkeits",         "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("erschöpfung",         "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("erschoepfung",        "muedigkeitssymptomatik_chronische_erschoepfung_v1_0"),
    ("neurodermitis",       "neurodermitis_atopisches_ekzem_v1_0"),
    ("atopisch",            "neurodermitis_atopisches_ekzem_v1_0"),
    ("post-zoster",         "post_zoster_neuralgie_v1_0"),
    ("post zoster",         "post_zoster_neuralgie_v1_0"),
    ("zoster",              "post_zoster_neuralgie_v1_0"),
    ("psoriasis",           "psoriasis_v1_0"),
    ("schuppenflechte",     "psoriasis_v1_0"),
    ("trigeminus",          "trigeminus_neuralgie_v1_0"),
]


def _infer_cluster_from_hauptbeschwerde(text: str | None, valid_keys: list[str]) -> str:
    """Return storage_key inferred from Hauptbeschwerde text, or '' if no match."""
    if not text:
        return ""
    normalized = text.strip().lower()
    for keyword, key in _KEYWORD_TO_CLUSTER:
        if keyword in normalized and key in valid_keys:
            return key
    return ""


class ScreenSummaryReview:

    def __init__(self, page: ft.Page, controller) -> None:
        self._page = page
        self._controller = controller

    def render(self) -> None:
        page       = self._page
        controller = self._controller
        summary    = controller.state.summary

        fields = [
            ft.TextField(
                label=label,
                value=getattr(summary, attr),
                multiline=True,
                min_lines=2,
                max_lines=4,
                expand=True,
            )
            for label, attr in _FIELDS
        ]

        # --- Cluster selection ---
        available = list_available_with_names()  # list of (storage_key, display_name)

        # Determine initial selection (priority chain):
        #   1. manual user selection preserved in state
        #   2. deterministic inference from Hauptbeschwerde
        #   3. empty / unselected (no fallback to first alphabetical item)
        valid_keys = [sk for sk, _ in available]
        prev_key = controller.state.selected_cluster_id or ""
        if prev_key in valid_keys:
            initial_key = prev_key
        else:
            initial_key = _infer_cluster_from_hauptbeschwerde(
                summary.most_burdensome, valid_keys
            )

        cluster_dropdown = ft.Dropdown(
            label="Cluster auswählen",
            value=initial_key,
            options=[
                ft.dropdown.Option(key=sk, text=name)
                for sk, name in available
            ],
            width=320,
        )

        def _collect() -> CaseSummary:
            return CaseSummary(
                main_complaints       = summary.main_complaints,
                most_burdensome       = fields[0].value.strip(),
                priority_complaint    = fields[1].value.strip(),
                additional_complaints = fields[2].value.strip(),
            )

        def on_pilot_composer(e: ft.ControlEvent) -> None:
            selected_key = cluster_dropdown.value or initial_key
            controller.show_pilot_composer(_collect(), storage_key=selected_key)

        def on_zurueck(e: ft.ControlEvent) -> None:
            controller.show_screen_2()

        page.add(
            ft.Text("AUFNAHME TCM KLINIK", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),
            ft.Text("Fallübersicht prüfen", size=16),
            ft.Container(height=16),
            *fields,
            ft.Container(height=16),
            ft.Column(
                controls=[
                    ft.Text(
                        "Cluster für Pilot-Composer:",
                        size=13,
                        color=_C_TEXT_SECONDARY,
                    ),
                    cluster_dropdown,
                ],
                spacing=6,
            ),
            ft.Container(height=16),
            ft.Row(
                controls=[
                    ft.OutlinedButton("← Zurück zum Interview", style=ft.ButtonStyle(color=_C_ACCENT), on_click=on_zurueck),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Weiter → Pilot-Composer",
                        icon=ft.Icons.SCIENCE_OUTLINED,
                        bgcolor=_C_ACCENT,
                        color=ft.Colors.WHITE,
                        on_click=on_pilot_composer,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
