# LWS Patterns — AI-Derived from M54.86 Corpus

**Source:** 368 unique M54.86 clinical texts (database001, 2311 documents)
**Method:** sentence-transformer embedding (paraphrase-multilingual-MiniLM-L12-v2) → K-means (k=3) → corpus-based archetype curation
**Date:** 2026-03-25

---

## LWS1 — Mechanisch-chronisches LWS-Syndrom

**Final text:**

> Chronische LWS-Beschwerden, ziehend-drückend, lumbosakral betont. Verstärkung bei längerem Sitzen, Stehen und Bücken; Besserung durch Wärme und Ruhe. Keine Ausstrahlung. Rezidivierender Verlauf über mehrere Jahre, belastungsabhängige Schmerzspitzen.

**Source clusters:** [1]
**Differentiator:** Rein mechanisches Muster ohne Ausstrahlung und ohne strukturelle Grunderkrankung
**Patient fit:** Berufstätige mittleren Alters mit sitzender oder stehender Tätigkeit, langjährige LWS-Anamnese

---

## LWS2 — LWS-Syndrom mit Beinausstrahlung

**Final text:**

> LWS-Schmerzen mit Ausstrahlung in Gesäß und Bein, teils bis Unterschenkel. Kribbeln und Taubheitsgefühl in der betroffenen Extremität. Belastungsabhängige Verstärkung, Linderung durch Entlastung und Liegen. Ischialgiformes Bild, häufig rezidivierend.

**Source clusters:** [1, 2]
**Differentiator:** Radikuläre oder pseudoradikuläre Ausstrahlung mit neuraler Begleitsymptomatik
**Patient fit:** Patienten mit ausgeprägter Beinbeteiligung, oft Verdacht auf BSV oder Wurzelreizung ohne gesicherte OP-Indikation

---

## LWS3 — Degeneratives LWS-Syndrom / Post-BSV

**Final text:**

> Chronisch-degeneratives LWS-Syndrom bei bekanntem Bandscheibenvorfall bzw. Z.n. Nukleotomie / Spondylodese. Persistierende LWS-Schmerzen, wechselnde Intensität, teils Ausstrahlung. Funktionell eingeschränkte Sitztoleranz und Gehstrecke. Langjährige Krankengeschichte mit multiplen Vortherapien.

**Source clusters:** [0, 2]
**Differentiator:** Strukturelle/degenerative Grundlage (BSV, Spondylarthrose, Osteochondrose) oder postoperativer Status
**Patient fit:** Ältere Patienten oder Patienten mit langer Leidensgeschichte, oft mit stationären Voraufenthalten

---

## Coverage Estimate

| Metric | Value |
|--------|-------|
| Total unique M54.86 texts | 368 |
| Texts covered by archetypes (LWS1+LWS2+LWS3) | 275 (74.7%) |
| Outlier text count | 93 (25.3%) |
| Outlier profile | LWS als Komorbidität in komplexen Mehrfachdiagnose-Fällen |

**Coverage note:** The 25% outliers predominantly represent cases where LWS is listed alongside dominant diagnoses from other systems (oncology, neurology, psychiatry). The three archetypes cover the primary LWS presentation spectrum adequately for template use.

---

## Usage in Aufnahme-Schablone

These patterns are intended as **selectable text blocks** in the TCM intake template (Aufnahme-Schablone) under the `Somatische Diagnosen` / `Derzeitige Beschwerden` section.

- Select **LWS1** for patients with purely mechanical, non-radiating chronic low back pain
- Select **LWS2** for patients with leg radiation, neurological signs, or ischialgia
- Select **LWS3** for patients with structural diagnosis (BSV, post-surgical) or long degenerative history
- Adjust free-text details after selection to match individual patient presentation
