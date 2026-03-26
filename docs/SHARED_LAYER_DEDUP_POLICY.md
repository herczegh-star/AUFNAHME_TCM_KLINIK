# SHARED_LAYER_DEDUP_POLICY

## 1. Purpose

The system uses two parallel data sources for draft generation:
- **cluster blocks** (`ai_draft_library.json`) — cluster-specific, pre-authored clinical phrases
- **shared pain items** (`shared_pain_layer_v2.json`) — transferable symptom attributes across clusters

Both sources can describe overlapping clinical content. Without explicit policy, a composer could render the same information twice in different formulations, inflating the output and violating the Controlled Clinical Compression principle.

This document defines the dedup policy that governs how a future composer must merge these two layers.

Invariants:
- The pipeline remains deterministic
- Shared layer is a supplementary micro-layer, not a second parallel cluster text
- Final output must read as one coherent clinical sentence, not a concatenation of two sources

---

## 2. Architectural Principle

```
cluster layer   = clinical framing
                  (anatomical anchor, core symptom phrasing, cluster-idiomatic language)

shared layer    = transferable symptom attributes
                  (character, aggravating, relieving, functional, radiation, overlays)

composer        = merge + suppression + narrative rendering
                  (decides what is already covered, what to add, in what order)
```

The cluster layer provides the sentence skeleton. The shared layer provides optional enrichment. The composer suppresses shared items that are already semantically covered by cluster blocks.

---

## 3. Precedence Rules

When both layers describe the same clinical content:

1. **Cluster-specific text takes precedence** — it is pre-authored and cluster-idiomatic
2. **Shared pain items are rendered only if not already covered** by a cluster block
3. **Nothing is inferred or generated** beyond what both layers explicitly provide

A shared item is considered "already covered" if:
- A cluster block of the same semantic type is present in `blocks_used`
- The cluster block's `semantic` dict matches the shared item's content category

---

## 4. Dedup Categories

### A — Safe to render (cluster blocks rarely cover this)
Shared items that cluster blocks typically do not duplicate:

- `pain_temporality` — cluster blocks rarely encode duration/pattern
- `pain_intensity` — almost never in current cluster blocks
- `context` — post-op, progression notes — never in cluster blocks

### B — Render only if not covered by cluster block
Shared items with a matching cluster block type:

- `pain_character` → suppress if cluster MODIFIER `modifier_type=character` present for same value
- `aggravating_mechanical` / `aggravating_general` → suppress if cluster MODIFIER `modifier_type=aggravating_factor` matches
- `relieving_passive` / `relieving_therapy` → suppress if cluster MODIFIER `modifier_type=relieving_factor` matches
- `pain_radiation` → suppress if cluster MODIFIER `modifier_type=radiation` present
- `functional_mobility` / `functional_general` → suppress if cluster FUNCTIONAL_IMPACT matches `limitation_type`

### C — Never render directly, support logic only
Used for family routing and module gating, not for text output:

- `pain_laterality` — laterality is already encoded in CORE_SYMPTOM block (`semantic.side`); rendering it again from shared layer would duplicate

### D — Overlay-only, explicit-input-only
Never render without explicit `associated_symptoms` input:

- `neuro_sensory`
- `cephalgic_features`
- `visceral_relations`

---

## 5. Module-by-Module Policy

### `pain_character`
- Represents: pain quality (ziehend, stechend, dumpf, ...)
- Renderable: yes, if no matching cluster character MODIFIER present
- Suppress when: `blocks_used` contains MODIFIER `modifier_type=character` with same value
- Conflict: high — LWS/HWS cluster blocks explicitly include character modifiers

### `pain_laterality`
- Represents: side (links, rechts, beidseits)
- Renderable: **no** — laterality is part of CORE_SYMPTOM block text; always covered
- Suppress when: always (category C)
- Conflict: total — CORE block already encodes laterality in its language variants

### `pain_radiation`
- Represents: anatomical radiation target
- Renderable: yes, if no cluster radiation MODIFIER present
- Suppress when: `blocks_used` contains MODIFIER `modifier_type=radiation`
- Conflict: moderate — LWS/HWS have explicit radiation blocks for Bein/Gesäß/Kopf/Arm

### `pain_intensity`
- Represents: severity qualifier (leicht, mittelgradig, stark, ausgeprägt)
- Renderable: yes — no current cluster block encodes intensity
- Suppress when: never (currently)
- Conflict: none with current library

### `pain_temporality`
- Represents: temporal pattern (chronisch, intermittierend, belastungsabhängig, progredient)
- Renderable: yes — no current cluster block encodes this
- Suppress when: never (currently)
- Conflict: none with current library

### `aggravating_mechanical`
- Represents: mechanical load as aggravating factor
- Renderable: yes, if no matching cluster aggravating MODIFIER present
- Suppress when: `blocks_used` contains MODIFIER `modifier_type=aggravating_factor` with matching trigger
- Conflict: high — LWS has `lws_mod_aggravating_sitzen`; HWS has Bildschirm block

### `aggravating_general`
- Represents: non-mechanical aggravating (Kälte, Stress)
- Renderable: yes — rarely covered by cluster blocks
- Suppress when: if cluster block with same trigger exists
- Conflict: low currently

### `relieving_passive`
- Represents: passive relief (Wärme, Ruhe, Liegen, Bewegung)
- Renderable: yes, if no matching cluster relieving MODIFIER present
- Suppress when: `blocks_used` contains MODIFIER `modifier_type=relieving_factor` with matching trigger
- Conflict: high — LWS/HWS have explicit Wärme blocks

### `relieving_therapy`
- Represents: therapeutic relief (Massage, KG, manuelle Therapie)
- Renderable: yes — cluster blocks currently don't include therapy modalities
- Suppress when: if future cluster blocks encode therapy
- Conflict: low currently

### `functional_mobility`
- Represents: mobility limitations (sitting_tolerance, walking_distance, bending, lifting)
- Renderable: yes, if no matching cluster FUNCTIONAL_IMPACT present
- Suppress when: `blocks_used` contains FUNCTIONAL_IMPACT with same `limitation_type`
- Conflict: high — LWS has `lws_func_sitztoleranz` and `lws_func_gehstrecke`

### `functional_general`
- Represents: general capacity (sleep_quality, daily_function, general_capacity)
- Renderable: yes — no current cluster block covers these
- Suppress when: if future cluster blocks add sleep/capacity items
- Conflict: low currently

### `neuro_sensory`
- Represents: neurogenic sensory symptoms (kribbeln, taubheit, paraesthesien)
- Renderable: yes, if overlay active AND explicit `associated_symptoms` input
- Suppress when: input absent, or overlay not active for cluster
- Conflict: low — not yet in cluster blocks; future HWS expansion may add

### `visceral_relations`
- Represents: visceral associations (Nahrungsbezug, Stuhlbezug, Blähungen)
- Renderable: yes, if visceral family active AND explicit input
- Suppress when: cluster already encodes visceral context
- Conflict: moderate for Reizdarm if cluster blocks added later

### `cephalgic_features`
- Represents: cephalgic features (Übelkeit, Lichtempfindlichkeit, Lärmempfindlichkeit)
- Renderable: yes, if cephalgic overlay active AND explicit input
- Suppress when: input absent
- Conflict: low — HWS associated_symptoms rarely encode these currently

### `context`
- Represents: clinical context notes (post-op, renewed progression, no morphologic correlate)
- Renderable: yes — no cluster block covers this
- Suppress when: never (category A)
- Conflict: none

---

## 6. Cluster-Specific Dedup Notes

### LWS-Syndrom
High overlap between cluster blocks and shared items for:
- `pain_character`: cluster has `lws_mod_charakter_ziehend`, `lws_mod_charakter_stechend` → suppress shared `pain_character` for matching values
- `aggravating_mechanical`: cluster has `lws_mod_aggravating_sitzen` → suppress `langes_sitzen` from shared layer
- `relieving_passive`: cluster has `lws_mod_relieving_waerme` → suppress `waerme`
- `functional_mobility`: cluster has `lws_func_sitztoleranz`, `lws_func_gehstrecke` → suppress matching shared items
- `pain_radiation`: cluster has `lws_mod_ausstrahlung_bein`, `lws_mod_ausstrahlung_gesaess` → suppress matching shared radiation

Safe to render from shared layer (not covered by current LWS blocks):
- `pain_intensity`, `pain_temporality`, `aggravating_general` (Kälte), `relieving_therapy`, `functional_general`, `context`

### HWS-Syndrom
Similar overlap profile to LWS:
- `pain_character`: cluster has ziehend, stechend, dumpf → suppress matches
- `aggravating_mechanical`: cluster has Bildschirm block → suppress `längere_bildschirmarbeit`
- `relieving_passive`: cluster has Wärme → suppress
- `functional_mobility`: cluster has `hws_func_kopfrotation` → suppress `head_rotation`
- `pain_radiation`: cluster has Kopf/Arm radiation → suppress matches

Cephalgic overlay (`cephalgic_features`) is HWS-specific but not yet in cluster blocks → safe to render if input present.

### Reizdarm / funktionelle Verdauungsbeschwerden
No cluster blocks exist yet. Full shared layer rendering is possible for:
- `pain_character`, `pain_temporality`, `visceral_relations`, `functional_general`

When cluster blocks are added: `visceral_relations` will likely have high overlap and need suppression rules.

### Polyneuropathie
Primary family: neurogenic. No cluster blocks exist yet.
- `neuro_sensory` is the dominant module — safe to render when input present
- `pain_character` + `pain_radiation` safe to render
- No current conflict

### Fibromyalgie
Primary family: centralized. No cluster blocks exist yet.
- `pain_character`, `pain_temporality`, `functional_general` safe to render
- `pain_intensity` relevant — safe to add
- Caution: avoid stacking too many modifiers (Content Philosophy rule 4)

---

## 7. Composer Safety Rules

1. **No information twice** — if a cluster block and a shared item describe the same fact, render only the cluster block's phrasing
2. **No implicit inference** — do not render shared items not present in `shared_pain_items_selected`
3. **Overlays require explicit input** — `neuro_sensory`, `cephalgic_features`, `visceral_relations` must have matching `associated_symptoms` in input
4. **Shared layer must not inflate text** — adding shared items should produce at most 1–2 additional sentence segments; never produce encyclopedic enumeration
5. **max_select respected** — composer must not render more items per module than `max_select` allows
6. **Category C modules never rendered** — `pain_laterality` is a logic helper only
7. **Context is optional** — `context` items enrich but are never required; omit if text is already sufficient

---

## 8. Integration Readiness

### Safe for first composer integration (low conflict risk)
- `pain_intensity` — no cluster block overlap, single slot value, safe to prepend
- `pain_temporality` — no overlap, single item, clear sentence position
- `aggravating_general` (Kälte, Stress) — rarely covered by cluster blocks
- `relieving_therapy` — not in current cluster blocks

### Experimental / do not render yet
- `pain_character` — high overlap with LWS/HWS cluster blocks; suppression logic must be validated first
- `functional_mobility` — high overlap; requires reliable semantic matching against `blocks_used`
- `neuro_sensory` — overlay mechanics correct but clinical rendering patterns not yet designed
- `cephalgic_features` — same as neuro_sensory
- `pain_radiation` — overlap with cluster radiation blocks; requires target matching

### Requires explicit cluster block suppression logic before use
- `aggravating_mechanical`
- `relieving_passive`
- `functional_mobility`
- `pain_character`
- `pain_radiation`
