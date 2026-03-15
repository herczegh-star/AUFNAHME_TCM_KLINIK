# AUFNAHME_TCM_KLINIK

Personal clinical documentation assistant for the admission workflow in a TCM clinic.

The system helps physicians generate the section
**"Derzeitige Beschwerden (somatisch)"** in standardized German clinical language.

---

## Project idea

The user does not manually choose templates.

Instead the physician provides structured symptom information, for example:

* localisation
* symptom type
* character of pain
* time course
* aggravating factors
* associated symptoms

The system then:

1. builds a **symptom profile**
2. selects the most suitable template from `template_library.json`
3. fills template slots (e.g. `[Region]`, `[Gelenk]`)
4. generates final clinical text in **Verdichtungsstil**

---

## Architecture

See project architecture:

docs/ARCHITEKTURA.md

---

## Project structure

```
AUFNAHME_TCM_KLINIK
│
├─ core        # application logic
├─ data        # template database
├─ ui          # Flet GUI
├─ docs        # architecture documentation
└─ main.py
```

---

## Setup

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running the application

Always run from the **project root directory**:

```bash
python ui/app.py
```

Using the virtual environment (recommended):

```bash
venv\Scripts\activate
python ui/app.py
```

> The app prints the active Python executable and version on startup
> to confirm the correct interpreter is used.

---

## Status

Early MVP stage.

Current focus: **core text generation engine**
