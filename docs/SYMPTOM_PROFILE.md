# SYMPTOM_PROFILE

Projekt: **AUFNAHME_TCM_KLINIK**

Tento dokument definuje univerzální strukturu symptomového profilu pro generování sekce  
**„Derzeitige Beschwerden (somatisch)”**.

Cílem je vytvořit jednotný model, který bude možné použít napříč různými symptomovými skupinami, například:

- LWS-Syndrom
- HWS-Syndrom
- Gelenkbeschwerden
- Migräne / Kopfschmerzen
- Reizdarm / funktionelle Verdauungsbeschwerden
- Fibromyalgie / Ganzkörperschmerzen
- Polyneuropathische Beschwerden

---

## Základní princip

Symptomový profil představuje **strukturovaný mezistupeň** mezi vstupem uživatele a finálním klinickým textem.

Workflow:

User input  
↓  
Symptomprofil  
↓  
Template Matching  
↓  
Template Filling  
↓  
Final Clinical Text

---

## Univerzální pole symptomového profilu

### 1. Symptomgruppe

Hlavní symptomová skupina.

Příklady:

- LWS-Syndrom
- HWS-Syndrom
- Migräne
- Reizdarm
- Fibromyalgie
- Polyneuropathie
- Gelenkbeschwerden

Použití:
- výběr odpovídajícího templatu

---

### 2. Lokalisation

Hlavní lokalizace obtíží.

Příklady:

- LWS
- HWS
- rechtes Knie
- linker Unterbauch
- beide Füße
- Stirn
- Hinterkopf
- Schulter-Nacken-Bereich

Použití:
- doplnění lokalizačních slotů v templatu

---

### 3. Seite / Betonung

Strana nebo převaha obtíží.

Příklady:

- rechts
- links
- rechtsbetont
- linksbetont
- beidseits
- einseitig
- wechselnd

Použití:
- laterální specifikace symptomu

---

### 4. Dauer

Doba trvání obtíží.

Příklady:

- seit 5 Jahren
- seit mehreren Jahren
- seit der Jugend
- seit 3 Monaten
- seit der COVID-19-Infektion

Použití:
- doplnění časového rámce do templatu

---

### 5. Verlauf / Progression

Vývoj obtíží v čase.

Příklady:

- progredient
- fluktuierend
- schubweise
- intermittierend
- in den letzten 2 Jahren verschlechtert
- aktuell stabil

Použití:
- popis dynamiky symptomu

---

### 6. Charakter

Charakter obtíží nebo bolesti.

Příklady:

- stechend
- ziehend
- dumpf
- pochend
- brennend
- drückend
- krampfartig
- kolikartig

Použití:
- doplnění bolesti / symptomové kvality

---

### 7. Ausstrahlung

Vyzařování obtíží.

Příklady:

- ins linke Bein
- in beide Beine
- in Schulter und Arm
- bis in die Unterschenkel
- keine Ausstrahlung

Použití:
- doplnění radiačního patternu

---

### 8. Trigger / Verschlechterung

Faktory zhoršující symptomy.

Příklady:

- bei Belastung
- bei längerem Sitzen
- bei längerem Stehen
- unter Stress
- bei Kälte
- nach dem Essen
- nachts

Použití:
- modifikující faktory

---

### 9. Linderung

Faktory vedoucí ke zlepšení.

Příklady:

- Wärme
- Ruhe
- Schonung
- Dunkelheit
- Bewegung
- manuelle Therapie
- physiotherapeutische Maßnahmen

Použití:
- pozitivně modifikující faktory

---

### 10. Begleitsymptome

Doprovodné symptomy.

Příklady:

- Übelkeit
- Lichtempfindlichkeit
- Geräuschempfindlichkeit
- Blähungen
- Völlegefühl
- Taubheitsgefühle
- Kribbeln
- muskuläre Verspannungen
- Schlafstörungen

Použití:
- rozšíření klinického popisu

---

### 11. Funktionelle Einschränkung

Funkční dopad obtíží.

Příklady:

- eingeschränkte Belastbarkeit
- Gangunsicherheit
- Einschränkung beim Treppensteigen
- reduzierte Feinmotorik
- verminderte Greifkraft
- Rückzugsbedürfnis während Attacken

Použití:
- popis praktického dopadu na běžný život

---

### 12. Bekannte Diagnose / Kontext

Známá diagnóza nebo klinický kontext.

Příklady:

- bekannte Arthrose
- bekannte Colitis ulcerosa
- nach COVID-19
- nach Trauma
- im Rahmen einer Fibromyalgie
- bei bekannter Polyneuropathie

Použití:
- zasazení symptomu do širšího klinického rámce

---

## Minimum Useful Profile (pro první implementaci)

Pro první verzi template filling vrstvy budou povinná nebo primárně využívaná tato pole:

- Symptomgruppe
- Lokalisation
- Dauer
- Verlauf / Progression
- Charakter
- Ausstrahlung
- Trigger / Verschlechterung
- Linderung
- Begleitsymptome

Tato sada je dostatečná pro první praktické použití zejména u:

- LWS-Syndrom
- HWS-Syndrom
- Gelenkbeschwerden
- části Fibromyalgie

---

## Příklad symptomového profilu – LWS-Syndrom

Symptomgruppe: LWS-Syndrom  
Lokalisation: LWS  
Seite / Betonung: linksbetont  
Dauer: seit 5 Jahren  
Verlauf / Progression: in den letzten 2 Jahren verschlechtert  
Charakter: stechend, pochend  
Ausstrahlung: in die Beine  
Trigger / Verschlechterung: bei Belastung  
Linderung: Wärme  
Begleitsymptome:  
Funktionelle Einschränkung:  
Bekannte Diagnose / Kontext:

---

## Příklad symptomového profilu – Migräne

Symptomgruppe: Migräne  
Lokalisation: einseitig  
Seite / Betonung: links  
Dauer: seit der Jugend  
Verlauf / Progression: mehrfach monatlich  
Charakter: pochend  
Ausstrahlung:  
Trigger / Verschlechterung: Stress  
Linderung: Ruhe, Dunkelheit  
Begleitsymptome: Übelkeit, Lichtempfindlichkeit  
Funktionelle Einschränkung: Rückzugsbedürfnis  
Bekannte Diagnose / Kontext:

---

## Architektonický význam

Symptomový profil slouží jako **standardizovaná datová vrstva**, která umožní:

- konzistentní výběr templatu
- strukturované doplňování slotů
- rozšíření systému na další symptomové skupiny
- zachování klinického stylu při současném zvýšení flexibility

Tento model je základem pro další vrstvu systému:

**Template Filling Layer**