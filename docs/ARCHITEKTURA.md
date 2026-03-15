# Architektura výběru templatu

Projekt **AUFNAHME_TCM_KLINIK** je koncipován jako hybridní systém, který spojuje:

- řízenou interakci s uživatelem
- symptomovou klasifikaci
- sémantický výběr templatu z databáze `template_library.json`

## Princip fungování

Uživatel nevybírá konkrétní template ručně, ale zadává pouze stručné
významové charakteristiky obtíží, například:

- lokalizaci
- typ symptomu
- charakter bolesti
- časový průběh
- zhoršující a zlepšující faktory
- doprovodné symptomy

Na základě těchto údajů systém nejprve vytvoří **symptomový profil**
a přiřadí jej k odpovídající **symptomové skupině**.

Následně proběhne **sémantické párování** s databází
`template_library.json`, při němž je vybrán template s nejvyšší
významovou shodou, nikoli pouze na základě mechanické shody klíčových slov.

## Slot filling

Pokud template obsahuje proměnné sloty například:

- `[Region]`
- `[Gelenk]`
- `[Charakter]`

systém je doplní podle zadaných údajů.

Template je poté převeden do **finální klinické formulace v němčině**.

## Cíl systému

Cílem architektury je, aby uživatel zadával především:

- obsah
- význam obtíží

zatímco systém zajistí:

- výběr nejvhodnější formulace
- správný jazykový tvar
- konzistentní **Verdichtungsstil**

## Poznámka k vývoji

Architektura nevznikla hotově na začátku projektu,
ale postupně se vykrystalizovala během práce,
analýzy reálných klinických textů
a tvorby symptomových modulů.