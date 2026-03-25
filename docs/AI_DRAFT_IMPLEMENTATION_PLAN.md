# AI-DRAFT IMPLEMENTATION PLAN
## Projekt: AUFNAHME_TCM_KLINIK

---

# 1. PURPOSE

This document translates architecture into implementation steps.

It defines:
- modules
- file structure
- first implementation steps

---

# 2. TARGET STRUCTURE

Recommended modules:

core/
  ai_draft/
    block_model.py
    block_loader.py
    block_selector.py
    rule_engine.py
    draft_composer.py
    language_refiner.py

data/
  ai_draft/
    ai_draft_library.json

docs/
  AI_DRAFT_ARCHITECTURE_SPEC.md
  AI_DRAFT_IMPLEMENTATION_PLAN.md

---

# 3. CORE COMPONENTS

## 3.1 Block Model
- defines structure of block
- validation of fields

## 3.2 Block Loader
- loads JSON database
- validates structure

## 3.3 Block Selector
- selects relevant blocks
- based on input semantics

## 3.4 Rule Engine
- enforces compatibility
- prevents conflicts

## 3.5 Draft Composer
- builds draft structure
- orders blocks

## 3.6 Language Refiner
- optional AI layer
- only stylistic changes

---

# 4. IMPLEMENTATION ORDER

## STEP 1
Create block model (STRICT)

## STEP 2
Create minimal JSON library (manual)

## STEP 3
Implement loader

## STEP 4
Implement simple selector

## STEP 5
Implement rule engine (basic)

## STEP 6
Compose draft WITHOUT AI

## STEP 7
Add AI refinement

---

# 5. FIRST PILOT

Use:
- ONE cluster (recommended: LWS)

Goals:
- create 5–10 blocks
- compose real draft
- validate logic

---

# 6. IMPORTANT RULES

DO NOT:
- use AI for content generation
- mix semantic and text layers
- create large database immediately

DO:
- start small
- validate manually
- iterate

---

# 7. DEFINITION OF DONE

Pilot is successful if:
- draft works without AI
- blocks combine correctly
- output is clinically valid

---

# 8. NEXT STEPS

After pilot:
- extend clusters
- improve scoring
- refine rules
- expand database

---

# FINAL NOTE

Implementation MUST follow:
AI_DRAFT_ARCHITECTURE_SPEC.md