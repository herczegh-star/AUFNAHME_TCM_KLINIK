# SOFTWARE_ARCHITEKTUR

Projekt: **AUFNAHME_TCM_KLINIK**

Tento dokument popisuje softwarovou architekturu systému pro generování klinických textů v rámci příjmového procesu (Aufnahme) na TCM klinice.

Cílem architektury je oddělit **klinickou logiku** od **uživatelského rozhraní** a vytvořit modulární systém, který bude možné postupně rozšiřovat.

---

# Architektonický princip

Projekt je navržen jako **vrstvený systém (layered architecture)**.

Hlavní vrstvy:

1. **Core layer** – aplikační logika systému
2. **Data layer** – databáze templátů
3. **UI layer** – tenké grafické rozhraní

---

# Core Layer

Umístění:

```
core/
```

Tato vrstva obsahuje veškerou logiku systému.

Je zcela nezávislá na grafickém rozhraní.

## Moduly

### models.py

Definuje datové struktury používané v systému.

Například:

* SymptomInput
* TemplateRecord
* GenerationResult

---

### template_repository.py

Zodpovídá za načítání templátů z databáze.

Zdroj dat:

```
data/template_library.json
```

Funkce modulu:

* načtení templátů
* jejich reprezentace jako objektů
* předání do dalších částí systému

---

### template_matcher.py

Provádí výběr nejvhodnějšího templatu.

Na základě:

* symptomového profilu
* významové podobnosti
* klíčových slov

V budoucnu může být rozšířen o:

* embeddingy
* sémantické modely
* AI asistované párování

---

### slot_filler.py

Zodpovídá za doplnění proměnných slotů v templatu.

Například:

```
[Gelenk]
[Region]
[Charakter]
```

Tyto sloty jsou nahrazeny hodnotami získanými ze symptomového profilu.

---

### orchestrator.py

Hlavní řídicí modul systému.

Koordinuje celý proces generování textu.

Pracovní tok:

1. načtení templátů
2. výběr nejlepšího templatu
3. detekce slotů
4. doplnění slotů
5. vytvoření finálního textu

Orchestrator představuje **centrální řídicí vrstvu aplikace**.

---

# Data Layer

Umístění:

```
data/template_library.json
```

Tento soubor obsahuje databázi templátů používaných pro generování klinických textů.

Každý template obsahuje například:

* identifikátor
* název
* text templatu
* případné sloty

Příklad templatu:

```
Seit längerer Zeit bestehende Schmerzen im Bereich des [Gelenk].
```

---

# UI Layer

Umístění:

```
ui/
```

Grafické rozhraní bude implementováno pomocí knihovny **Flet**.

UI vrstva má pouze tyto úkoly:

* získat vstup od uživatele
* předat data orchestratoru
* zobrazit výsledek

Důležitý princip:

**UI nesmí obsahovat klinickou logiku.**

Veškeré rozhodování musí probíhat v **core layer**.

---

# Tok dat systémem

```
User Input
     ↓
SymptomInput
     ↓
Orchestrator
     ↓
Template Repository
     ↓
Template Matcher
     ↓
Slot Filler
     ↓
Final Clinical Text
```

---

# Designové principy

Architektura systému se řídí následujícími principy:

* oddělení odpovědností (separation of concerns)
* modulární struktura
* deterministické generování textu
* rozšiřitelný systém výběru templátů

---

# Budoucí rozšíření

Možná budoucí vylepšení systému:

* sémantické embeddingy pro výběr templatu
* symptomová ontologie
* inteligentní klasifikace symptomů
* integrace s klinickými systémy
* pokročilé jazykové korekce

---

# Stav projektu

Projekt se aktuálně nachází ve fázi **MVP (Minimum Viable Product)**.

Prioritou je vytvoření stabilního **core engine pro generování textu**, na který bude následně napojeno grafické rozhraní.
