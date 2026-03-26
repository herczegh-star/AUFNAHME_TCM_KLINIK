# CLINICAL_NARRATIVE_PATTERNS

## 1. Purpose

The selector (`SharedPainSelector`) produces a stable, alphabetically ordered dict of matched canonicals. This is a data structure, not a sentence.

The composer is responsible for:
- deciding clinical order of segments
- choosing appropriate formulations for each segment
- suppressing redundant content (per SHARED_LAYER_DEDUP_POLICY.md)
- rendering a single coherent clinical sentence

This document defines narrative patterns for the composer. It is a design specification, not an implementation.

---

## 2. Core Principle

```
internal deterministic order  ≠  clinical narrative order

alpha sort (selector)         →  tests, serialization, dedup logic
clinical order (composer)     →  readable, plausible, Verdichtungsstil output
```

The composer receives `shared_pain_items_selected` (alpha-sorted) and must apply its own narrative ordering rules per cluster.

---

## 3. Narrative Building Blocks

The following segment types can appear in a clinical sentence. Each maps to one or more source modules or block types.

| Segment type         | Source                                    | Notes |
|----------------------|-------------------------------------------|-------|
| Temporality          | `pain_temporality` (shared)               | Optional opener |
| Cluster anchor       | CORE_SYMPTOM block                        | Always present |
| Laterality           | CORE_SYMPTOM block (semantic.side)        | Encoded in block text, not re-rendered |
| Pain character       | MODIFIER character / `pain_character`     | 1–2 items max |
| Radiation            | MODIFIER radiation / `pain_radiation`     | 1 item max |
| Intensity            | `pain_intensity` (shared)                 | Single qualifier |
| Aggravating          | MODIFIER aggravating / `aggravating_*`    | 1–2 items; mechanical preferred |
| Relieving            | MODIFIER relieving / `relieving_*`        | 1–2 items |
| Functional impact    | FUNCTIONAL_IMPACT / `functional_mobility` | 1–2 items |
| Neuro-sensory        | `neuro_sensory` (overlay, explicit only)  | Short addendum |
| Cephalgic overlay    | `cephalgic_features` (overlay, explicit)  | Short addendum |
| Visceral relation    | `visceral_relations` (explicit only)      | Replace aggravating for visceral |
| Context              | `context` (shared)                        | Trailing sentence, optional |

---

## 4. Pattern Templates by Cluster

---

### LWS-Syndrom

**Preferred narrative order:**
```
[Temporality →] Cluster anchor → Character → Radiation → Aggravating → Relieving → Functional
```

**Optional segments:** Temporality, Radiation, Neuro-sensory (if kribbeln/taubheit present)

**Usually omit:** Intensity (not clinically distinctive here), Context (unless post-op)

**Schematic patterns:**

```
A — minimal:
  Schmerzen lumbal {side}, {character}.
  Verschlechterung bei {aggravating}.
  Teilweise Besserung durch {relieving}.

B — with radiation + functional:
  Schmerzen lumbal {side}, {character}, mit Ausstrahlung ins {radiation_target}.
  Verschlechterung bei {aggravating}.
  Teilweise Besserung durch {relieving}.
  {Functional impact}.

C — with temporality opener:
  {Temporality} — Schmerzen lumbal {side}, {character}.
  Verschlechterung bei {aggravating}.
  {Functional impact}.
```

---

### HWS-Syndrom

**Preferred narrative order:**
```
[Temporality →] Cluster anchor → Character → Radiation → Aggravating → Relieving → Functional → [Cephalgic overlay]
```

**Optional segments:** Temporality, Cephalgic overlay (explicit only), Neuro-sensory (explicit only)

**Usually omit:** Intensity, Visceral

**Schematic patterns:**

```
A — minimal:
  Schmerzen zervikal {side}, {character}.
  Verschlechterung bei {aggravating}.
  Kopfrotation {functional}.

B — with radiation + cephalgic:
  Schmerzen zervikal {side}, {character}, mit Ausstrahlung in {radiation_target}.
  Verschlechterung bei {aggravating}.
  Teilweise Besserung durch {relieving}.
  Begleitend: {cephalgic_item}.

C — with neuro overlay:
  Schmerzen zervikal {side}, {character}.
  Verschlechterung bei {aggravating}.
  Begleitend {neuro_sensory_item} im Bereich {side} Arm/Hand.
```

---

### Reizdarm / funktionelle Verdauungsbeschwerden

**Preferred narrative order:**
```
[Temporality →] Cluster anchor → Character → Visceral relation → Functional → [Context]
```

No aggravating_mechanical. No radiation. No laterality.

**Optional segments:** Temporality, Context (functional_discussion useful here)

**Usually omit:** Radiation, Laterality, Neuro-sensory, Cephalgic

**Schematic patterns:**

```
A — minimal:
  {Temporality} abdominelle Beschwerden, {character}.
  {Visceral relation}.
  {Functional impact: daily_function}.

B — with context:
  {Temporality} abdominelle Beschwerden, {character}.
  {Visceral relation}.
  Nach entsprechender Diagnostik kein morphologisches Korrelat.
  Diskussion einer funktionellen Genese.

C — minimal, no temporality:
  Abdominelle Beschwerden, {character}, {visceral_relation}.
  {Functional impact}.
```

---

### Polyneuropathie

**Preferred narrative order:**
```
[Temporality →] Cluster anchor → Character → Radiation / topography → Neuro-sensory → Functional → [Intensity]
```

No aggravating_mechanical. No relieving_therapy. Laterality may apply (bilateral typical).

**Optional segments:** Intensity (relevant here — severity matters), Functional

**Usually omit:** Cephalgic, Visceral, Context (unless no-morphologic-correlate relevant)

**Schematic patterns:**

```
A — minimal:
  {Temporality} Missempfindungen / Schmerzen {side}, {character}.
  Begleitend {neuro_sensory_item}.
  {Functional: daily_function oder walking_distance}.

B — with intensity:
  {Temporality} {intensity} ausgeprägte Missempfindungen {side}, {character}.
  Begleitend {neuro_sensory_items}.

C — with topographic radiation:
  Schmerzen {side}, {character}, mit {radiation_target}-Betonung.
  Begleitend {neuro_sensory_items}.
  Funktionell: {functional_item}.
```

---

### Fibromyalgie

**Preferred narrative order:**
```
[Temporality →] Cluster anchor → Character → Intensity → Aggravating (general only) → Functional (general) → [Context]
```

No radiation. No mechanical aggravating (Sitzen/Stehen inappropriate as primary framing). No neuro-sensory as leading element (can appear but not prominent).

**Optional segments:** Context (renewed_progression relevant)

**Usually omit:** Radiation, Laterality (diffuse = no single side), Aggravating_mechanical, Relieving_therapy (misleading in fibromyalgie context)

**Schematic patterns:**

```
A — minimal:
  {Temporality} diffuse Schmerzsymptomatik, {character}.
  Verschlechterung unter {aggravating_general: stress}.
  Allgemeine Belastbarkeit reduziert.

B — with intensity + context:
  {Temporality} {intensity} ausgeprägte diffuse Schmerzsymptomatik, {character}.
  Erneute Zunahme von Intensität und Frequenz der Beschwerden in den letzten Monaten.
  Schlafqualität beeinträchtigt.

C — minimal, no temporality:
  Diffuse Schmerzsymptomatik, {character}, {intensity}.
  {Functional: general_capacity}.
```

---

## 5. Clinical Style Rules

1. **Verdichtungsstil** — short, nominalized, passive-free where possible; no conjunctive reasoning
2. **No encyclopedic enumeration** — max 2 items per segment type in final text
3. **No diagnostic inference** — do not write "hinweisend auf", "vereinbar mit", "differential..."
4. **Explicit content only** — only render items present in `blocks_used` or `shared_pain_items_selected`
5. **Single coherent passage** — the output is 3–5 sentences, not a list
6. **Overlays are addenda, not expansions** — neuro/cephalgic/visceral content is appended briefly, never becomes the primary frame

---

## 6. Compression Rules

When the assembled text is too long:

**Drop first (lowest clinical impact):**
- `pain_temporality` — useful but not essential
- second relieving item if two are present
- `context` items (optional by definition)
- `pain_intensity` — often inferable from functional impact

**Keep as core information:**
- Cluster anchor (CORE_SYMPTOM)
- Primary pain character (1 item)
- Primary aggravating (1 item)
- Primary relieving (1 item)

**Keep if present in input:**
- Radiation target (clinically significant)
- Functional impact (1 item, most limiting one)

**Never drop:**
- CORE_SYMPTOM block text
- Any item explicitly marked `priority: "core"` in the selected modules

---

## 7. Example Micro-Patterns

These are formulation fragments, not full sentences. For pattern design reference only.

```
-- Temporality openers --
Seit mehreren Jahren ...
Chronisch rezidivierende ...
Intermittierende ...
Belastungsabhängige ...
In den letzten Monaten zunehmende ...

-- Character qualifiers --
... ziehenden Charakters
... stechend-ziehend
... dumpf-drückend
... mit brennender Komponente

-- Radiation --
... mit Ausstrahlung ins linke Bein
... mit Ausstrahlung in den Hinterkopf und linken Arm
... ohne Ausstrahlung  [only if radiation=False AND previously stated]

-- Aggravating --
Verschlechterung bei längerem Sitzen.
Zunahme bei Kälteexposition.
Verschlechterung bei körperlicher Belastung und Stress.

-- Relieving --
Teilweise Besserung durch Wärme.
Besserung in Ruhe und im Liegen.
Teilweise Ansprechen auf Massage.

-- Functional --
Sitztoleranz deutlich reduziert.
Gehstrecke eingeschränkt.
Kopfrotation schmerzhaft eingeschränkt.
Schlafqualität beeinträchtigt.
Alltagsbelastbarkeit reduziert.

-- Neuro overlay --
Begleitend Kribbelgefühl und Taubheitsgefühl im Bereich des rechten Arms.

-- Cephalgic overlay --
Begleitend Übelkeit und Lichtempfindlichkeit.

-- Visceral --
Beschwerden mit Bezug zur Nahrungsaufnahme.
Zusammenhang mit dem Stuhlgang.

-- Context --
Postoperativ zunächst kurzzeitige Besserung.
In den letzten Monaten erneute Zunahme von Intensität und Frequenz.
Nach entsprechender Diagnostik kein morphologisches Korrelat.
```
