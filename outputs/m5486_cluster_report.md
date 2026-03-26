# M54.86 Cluster Report

**ICD:** M54.86 (LWS-Syndrom)
**Total unique texts:** 365
**Clusters (best k):** 3  (silhouette k=3: 0.150 best of k=3..6)

---

## Cluster 0  (n=106)

LWS as a recurring comorbidity in complex multi-symptom presentations
(CFS, fibromyalgia, post-COVID, RA, widespread pain). LWS pain is documented
but not the primary complaint. Chronic course uniformly present.

**Recurring features (fraction of examples):**

  character       90%  ##################
  relieving       100% ####################
  chronicity      80%  ################
  functional      70%  ##############
  radiation_leg   20%  ####
  neuro           0%
  surgery_bsv     0%

**5 representative texts (excerpt):**

**[1]** Die Patientin wird mit einem komplexen psychosomatischen Beschwerdebild zur stationaeren Aufnahme vorgestellt. Chronische LWS-Schmerzen. Der Schmerzcharakter wird als stechend-ziehend beschrieben. Besserung durch Waerme und Ruhe.

**[2]** Seit einem schweren BSV im LWS-Bereich wuerden die Schmerzen immer staerker werden. Dauerhafte sowie attackenartig auftretende Schmerzen, verschiedenster Qualitaet mit Verstaerkung bei dynamischer Belastung sowie laengerem Gehen und Sitzen. Mal seien sie drueckend, ziehend, sowie stechend.

**[3]** Chronische Schmerzsymptomatik im LWS-Bereich seit der Jugend. Degenerative Veraenderungen der LWS mit Bandscheibenprolaps L2/3, Spondylarthrose L5/S1 sowie Osteochondrosen L1/2 und L5/S1.

**[4]** Intermittierende Schmerzen im LWS-Bereich, die sich in den letzten Monaten deutlich verstaerkt haben. Ziehend und dumpf. Schmerzerstaerkung bei laengerem Sitzen und Stehen. Besserung durch Waerme.

**[5]** Seit ueber 20 Jahren progrediente Schmerzen im LWS-Bereich. Schmerzausstrahlung rechts- und linksseitig in beide laterale Oberschenkel bis zu den Fersen. Schmerzerstaerkend: laengere Gehstrecken, langes Stehen, Sitzen.

---

## Cluster 1  (n=166)

Primary LWS group - patients where LWS is a leading complaint. Widest clinical
variety: pure mechanical, radiation, and post-BSV cases all present. Highest
rate of pain character and radiation documentation.

**Recurring features (fraction of examples):**

  character       100% ####################
  relieving       90%  ##################
  chronicity      90%  ##################
  aggravating     40%  ########
  radiation_leg   30%  ######
  neuro           10%  ##
  surgery_bsv     10%  ##
  functional      20%  ####

**5 representative texts (excerpt):**

**[1]** Seit ueber 20 Jahren intermittierend zunehmende Schmerzen im LWS-Bereich, ziehend. Ausstrahlung ins rechte Bein. Degeneratives LWS-Syndrom. Schmerzerstaerkung bei laengerem Stehen und Sitzen. Besserung durch Waermeapplikation und manuelle Therapie.

**[2]** Seit ueber zwanzig Jahren unter Dorsalgien im LWS-Bereich ohne Ausstrahlung. Schmerzen als stechend empfunden. Intermittierende Schmerzen, die bei Bewegung deutlich zunehmen. Schmerzerstaerkung bei Buecken und Treppensteigen.

**[3]** Seit etwa 15 Jahren unter Rueckenschmerzen im LWS-Bereich. LWS-Schmerzen mit Ausstrahlung ueber gluteal in den dorsolateralen Oberschenkel rechtsbetont. Kribbeln und Taubheitsgefuehl im Bereich beider Beine und Fuesse. Schmerzerstaerkung bei laengerem Gehen und Stehen.

**[4]** Seit ueber 6 Jahren Schmerzen im Bereich des thorakolumbalen Uebergangs. BSV L5/S1 konservativ behandelt. Schmerzen auf Ruecken und Rumpf ausgedehnt. Waerme und Entlastung lindern teilweise.

**[5]** Seit ueber sieben Jahren intermittierende Dorsalgien im unteren LWS-Bereich. Belastungsabhaengige Schmerzen, drueckend und stechend. Schmerzerstaerkung beim Buecken und Treppensteigen. Besserung durch Ruhe und Waerme.

---

## Cluster 2  (n=93)

Returning patients (bekannt im Hause) with established multi-year LWS history.
Documentation shorter per visit - references prior records. LWS often part of
multi-symptom complex. Highest surgery/BSV rate among examples.

**Recurring features (fraction of examples):**

  character       100% ####################
  relieving       100% ####################
  chronicity      80%  ################
  radiation_leg   40%  ########
  neuro           30%  ######
  surgery_bsv     50%  ##########
  functional      50%  ##########

**5 representative texts (excerpt):**

**[1]** Im Hause bekannt. Seit Jahren komplexes Krankheitsbild. Chronische LWS-Schmerzen, ziehend-stechend, mit Ausstrahlung in die Beine. Schmerzerstaerkung bei Belastung und langem Sitzen. Besserung durch Waerme und Ruhe.

**[2]** Im Hause bekannt, letzter Aufenthalt 2022. Seit ueber 8 Jahren unter zunehmender LWS-Symptomatik. Schmerzen dumpf-drueckend. Verschlechterung bei Stehen und Gehen. Besserung durch Physiotherapie und Waerme.

**[3]** Chronisches LWS-Syndrom seit zehn Jahren. Schmerzen ziehend, belastungsabhaengig. Sitztoleranz deutlich reduziert. Kurzzeitige Linderung durch Waermeapplikation.

**[4]** Seit mehreren Jahren intermittierende LWS-Schmerzen, schubweise. Stechend und drueckend. Gelegentliche Ausstrahlung in das linke Bein. Verschlechterung bei koerperlicher Belastung.

**[5]** Seit 10 Jahren LWS-Schmerzen, degenerative Veraenderungen. Schmerzcharakter dumpf-stechend. Kribbeln beidseits im Bereich der Unterschenkel und Fuesse. Besserung durch Entlastung und manuelle Therapie.

---

## Overall Feature Coverage (all 365 unique texts)

| Feature | Texts | Fraction |
|---------|-------|----------|
| Pain character (ziehend/stechend/dumpf/drueckend) | 337 | 92% |
| Relieving factors (Waerme/Ruhe/Liegen/manuelle Therapie) | 326 | 89% |
| Aggravating factors (Sitzen/Stehen/Belastung) | 311 | 85% |
| Chronicity (chronisch/seit Jahren/rezidivierend) | 241 | 66% |
| Radiation to leg/gluteal | 146 | 40% |
| Surgery/BSV/degenerative (structured) | 107 | 29% |
| Neuro symptoms (Kribbeln/Taubheit) | 73 | 20% |
| Functional limitation (specific) | 120 | 33% |

## Coverage by Pattern

| Pattern | Matched texts | Fraction |
|---------|---------------|----------|
| LWS1 (mechanical, no BSV, no leg radiation) | 92 | 25% |
| LWS2 (radiation to leg) | 146 | 40% |
| LWS3 (BSV/degenerative/post-op) | 107 | 29% |
| Union (LWS1+2+3) | 275 | 75% |
| Outliers (LWS as comorbidity, complex cases) | 93 | 25% |
