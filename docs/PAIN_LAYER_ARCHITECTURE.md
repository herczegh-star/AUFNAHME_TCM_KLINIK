# Pain Layer Architecture

## Co je shared pain layer

Shared pain layer je soubor klinicky znovupoužitelných modulů pro popis bolesti,
nezávislých na konkrétním clusteru. Místo duplikování bloků (ziehend u LWS, ziehend u HWS, ...)
existuje jeden kanonický modul `pain_character`, který mohou sdílet všechny clustery
patřící do stejné pain family.

**Soubor:** `data/ai_draft/shared_pain_layer_v2.json`

---

## Co je pain family matrix

Každý klinický cluster patří do jedné *primary pain family* a může mít 0–N *overlays*.

| Family       | Typické clustery                         | Klíčové moduly                                      |
|--------------|------------------------------------------|-----------------------------------------------------|
| mechanical   | LWS-Syndrom, HWS-Syndrom, Knie, Schulter | aggravating_mechanical, functional_mobility         |
| neurogenic   | Polyneuropathie, (overlay: LWS, HWS)     | neuro_sensory                                       |
| visceral     | Reizdarm, CED                            | visceral_relations                                  |
| cephalgic    | Kopfschmerzen, Migräne, (overlay: HWS)   | cephalgic_features                                  |
| pelvic       | Endometriose                             | visceral_relations                                  |
| centralized  | Fibromyalgie, (overlay: Polyarthritis)   | functional_general                                  |
| none         | Tinnitus, Müdigkeit                      | context only                                        |

---

## Jak funguje primary family + overlays

```
cluster_id: "hws_syndrom"
  primary_family: "mechanical"
    → allowed_modules: pain_character, pain_laterality, pain_radiation,
                       aggravating_mechanical, aggravating_general,
                       relieving_passive, relieving_therapy,
                       functional_mobility, context, ...
  overlays: ["neurogenic", "cephalgic"]
    → adds: neuro_sensory, functional_general, cephalgic_features

  final allowed_modules = union of all three families
```

Overlay přidává moduly, nikdy neodebírá. Union je deterministický.

---

## Datová struktura (shared_pain_layer_v2.json)

```
{
  "pain_families": {
    "<family_name>": {
      "allowed_modules": ["module_a", "module_b", ...]
    }
  },
  "modules": {
    "<module_name>": {
      "kind": "block_group" | "slot_group" | "template_group",
      "max_select": int,            // pro block_group
      "items": [                    // pro block_group
        { "canonical": str, "text": str, "priority": "core"|"optional"|... }
      ],
      "slot_name": str,             // pro slot_group + template_group
      "values": [str, ...]          // pro slot_group
    }
  },
  "cluster_family_map": [
    { "cluster_id": str, "primary_family": str, "overlays": [str, ...] }
  ]
}
```

---

## Co je aktuálně implementováno

| Komponenta | Status |
|---|---|
| `shared_pain_layer_v2.json` | ✓ pilot dataset (15 clusters, 13 modules, 6 families) |
| `shared_pain_loader.py` | ✓ loader s cache, family resolution, module access |
| `block_loader.py` | ✓ re-exportuje shared_pain_loader helpers |
| `block_selector.py` | ✓ `select_shared_pain_modules_for_cluster()` — vrací dostupné moduly |
| `draft_pipeline.py` | ✓ plní `cluster_family_info` + `shared_pain_modules_available` do výsledku |

---

## Co zatím implementováno NENÍ

- Mapování `normalized_input` na konkrétní canonical položky v modulech
  (např. input `character=["ziehend"]` → vyber `pain_character.items[canonical=ziehend]`)
- Integrace shared module textu do finálního draft textu (zatím jen `block_selector` vrací strukturu)
- Full cluster coverage (Schulter, Knie, Arthrose, Fibromyalgie, atd. nejsou v `ai_draft_library.json`)
- UI zobrazení shared pain modules ve screen_composer

---

## Další krok (navrhovaný)

**STEP 8 — Shared module content selection:**

Rozšířit `BlockSelector.select_shared_pain_modules_for_cluster()` tak, aby:
1. Přijal `normalized_input` (character, aggravating, relieving, ...)
2. Z každého allowed modulu vybral konkrétní `canonical` položky matching vstup
3. Vrátil `list[SharedModuleSelection]` vhodný pro `DraftComposer`

Teprve po tomto kroku lze shared layer fakticky zapojit do generování draft textu.

---

## Jak ověřit integraci

```python
from core.ai_draft.draft_pipeline import DraftPipeline

pipeline = DraftPipeline()
result = pipeline.run({
    "cluster": "LWS-Syndrom",
    "side": "beidseits",
    "character": ["ziehend"],
})

print(result.cluster_family_info)
# {"primary_family": "mechanical", "overlays": ["neurogenic"]}

print(result.shared_pain_modules_available)
# ["aggravating_general", "aggravating_mechanical", "context",
#  "functional_general", "functional_mobility", "neuro_sensory",
#  "pain_character", "pain_intensity", "pain_laterality",
#  "pain_radiation", "pain_temporality", "relieving_passive",
#  "relieving_therapy"]
```
