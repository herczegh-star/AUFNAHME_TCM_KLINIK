# AI-DRAFT ARCHITECTURE SPECIFICATION
## Projekt: AUFNAHME_TCM_KLINIK

---

# 0. PURPOSE

This document is a **binding specification**.

It defines:
- system philosophy
- data workflow
- block model
- composition rules

This document MUST be followed.
No deviation without redesign.

---

# 1. CORE PRINCIPLE

**The database is NOT a collection of texts.**  
**The database IS a model of clinical reality.**

Implications:
- meaning comes first
- text comes second
- AI MUST NOT generate medical content
- AI is ONLY a language refiner

---

# 2. ROLE OF AI

AI is allowed:
- language smoothing
- connecting blocks
- selecting variants

AI is NOT allowed:
- inventing symptoms
- adding medical meaning
- uncontrolled generation

Rule:
**AI controls language, NOT meaning**

---

# 3. DATA WORKFLOW

Pipeline:

DATASET  
→ EXTRACTION  
→ NORMALIZATION  
→ SEGMENTATION  
→ SEMANTIC ANNOTATION  
→ ABSTRACTION  
→ CLUSTERING  
→ BLOCK CREATION  
→ CURATION  
→ RULES  
→ LANGUAGE LAYER  
→ VALIDATION  
→ AI_DRAFT_LIBRARY

---

# 4. BLOCK DEFINITION

Block = structured unit of clinical meaning

---

## BLOCK TYPES

### CORE_SYMPTOM
- main complaint
- mandatory
- max 1–3

### MODIFIER
- modifies core
- cannot exist alone

### CONTEXT
- defines framework
- must not conflict

### ASSOCIATED_SYMPTOM
- secondary symptom

### FUNCTIONAL_IMPACT
- describes limitation

### TEMPORAL
- time evolution

### EXPERT
- advanced formulation

---

## BLOCK STRUCTURE

Each block MUST contain:

### IDENTIFICATION
- id
- cluster
- type

### SEMANTIC
- structured meaning

### COMPOSITION
- allowed_with
- forbidden_with
- requires

### LANGUAGE
- 1–3 variants

### QUALITY
- score
- source
- validated

---

# 5. COMPOSITION RULES

## ORDER
1. core
2. modifiers
3. context
4. associated
5. functional

---

## RULES

- at least 1 core
- no contradictions
- no redundancy
- medically plausible

---

# 6. SYSTEM REQUIREMENTS

System MUST:
- be deterministic
- be auditable
- be traceable

System MUST NOT:
- rely on free AI generation
- mix meaning and text

---

# 7. SUCCESS CRITERIA

- works without AI
- AI only refines
- outputs consistent
- no medical errors

---

# 8. FINAL PRINCIPLE

**First model reality. Then generate language.**