# AI_DRAFT_CONTENT_PHILOSOPHY

## Purpose

This document defines the core content philosophy of the AI-Draft system in the project AUFNAHME_TCM_KLINIK.

The system is designed to generate concise, clinically plausible summaries of patient complaints for the section:

**"Derzeitige Beschwerden (somatisch)"**

---

## What the system is NOT

The AI-Draft system is NOT:

- a diagnostic engine
- a full clinical documentation system
- a guideline-based medical reasoning tool
- an exhaustive symptom catalog

It does NOT aim to:

- provide complete symptomatology
- cover all possible variations of a syndrome
- replicate specialist-level diagnostic descriptions

---

## What the system IS

The system IS:

> **a section-optimized clinical abstraction layer**

It produces:

- short
- structured
- clinically plausible
- representative summaries

primarily for **chronic patients**.

---

## Core Principle

### Controlled Clinical Compression

The system performs:

> **reduction of complex clinical reality while preserving clinical plausibility**

This means:

- simplifying without distorting
- selecting without omitting essential meaning
- compressing without losing credibility

---

## Content Rules

### 1. Prefer Typical Over Complete

Include only:

- the most common
- the most representative
- the most clinically useful features

Avoid:

- rare manifestations
- edge cases
- highly specialized distinctions

---

### 2. Avoid Encyclopedic Descriptions

Do NOT:

- describe syndromes exhaustively
- reproduce textbook definitions
- mimic guideline-style checklists

---

### 3. Focus on Text Utility

Each element must justify itself by improving:

- readability
- clinical clarity
- practical usefulness of the final text

---

### 4. Limit Complexity

- Do not include all possible dimensions
- Do not stack too many modifiers
- Do not overfit rare patterns

---

### 5. Use Overlays Sparingly

Overlay layers (e.g. neurogenic, cephalgic):

- should only be used when they improve realism
- must not be applied automatically
- must not overload the base cluster

---

### 6. Context Is Optional

Context blocks (e.g. prior surgery, progression):

- are valuable but not mandatory
- should be used only when they add meaning
- should remain concise

---

### 7. No Diagnostic Reasoning

The system must NOT:

- infer diagnoses
- simulate differential diagnosis
- expand into explanatory reasoning

---

## Structural Implication

The system architecture should favor:

- modular blocks
- reusable patterns
- minimal but sufficient representations

over:

- maximal completeness
- theoretical correctness
- academic detail

---

## Summary

The AI-Draft system:

- does NOT aim to describe everything
- aims to describe the **right things**

It produces:

> **clinically believable, concise summaries — not perfect medical descriptions**

This philosophy must be respected in:

- database design
- block definitions
- template construction
- future extensions