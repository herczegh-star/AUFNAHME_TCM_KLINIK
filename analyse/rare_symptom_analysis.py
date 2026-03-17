"""
rare_symptom_analysis.py
------------------------
Extract rare (2-10 doc) medical symptom phrases from the
"Derzeitige Beschwerden" section of DOCX reports.

Outputs:
  outputs/rare_symptom_candidates.csv
  outputs/rare_symptom_examples.csv
"""

import os
import re
import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd
from docx import Document

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATASET_DIR = Path("dataset/aufnahmeberichte")
OUTPUT_DIR  = Path("outputs")

START_HEADING = "derzeitige beschwerden"
END_HEADING   = "vormedikation"

MIN_DOCS = 2
MAX_DOCS = 10
MAX_EXAMPLES = 5

# Minimum n-gram length (chars) to be considered meaningful
MIN_TERM_LEN = 6

# ---------------------------------------------------------------------------
# Generic German stopwords (extended for clinical boilerplate)
# ---------------------------------------------------------------------------

STOPWORDS = {
    "und", "die", "der", "das", "ein", "eine", "ist", "sich", "mit",
    "von", "auf", "dem", "den", "des", "bei", "aus", "auch", "nicht",
    "sie", "wie", "vor", "nach", "seit", "über", "unter", "durch",
    "aber", "oder", "als", "dass", "daß", "damit", "werden", "wurde",
    "haben", "habe", "hatte", "hat", "worden", "sind", "war", "wird",
    "kann", "mehr", "sehr", "noch", "schon", "alle", "immer", "wieder",
    "bereits", "sowie", "jedoch", "dabei", "bisher", "weiter", "zunächst",
    "zuletzt", "aktuell", "derzeit", "nunmehr", "erneut", "weiterhin",
    "ferner", "zudem", "ebenso", "insbesondere", "insgesamt", "außerdem",
    "zeigt", "zeigen", "gibt", "geben", "liegt", "liegen", "führt",
    "stellt", "beim", "ohne", "etwa", "laut", "daher", "bitte",
    "leide", "leiden", "leider", "leidet", "klagt", "klage", "klagen",
    "patientin", "patient", "herr", "frau", "berichtet",
    "aufenthalt", "klinik", "hause", "bekannt",
    "derzeitige", "seien", "habe", "hatte", "worden", "welche",
    "würden", "würde", "werde", "wolle", "wozu", "dabei", "hierbei",
    "handelt", "erhoffe", "vorliegenden", "unterlagen", "weiteren",
    "befinden", "besteht", "bestehe", "bestehen", "berichten",
    "nehmen", "nehme", "nimmt", "zeige", "zeigt", "zeigte",
    "beim", "ihre", "ihrer", "ihren", "ihrem", "seine", "seinen",
    "diesem", "dieser", "dieses", "diese", "jener", "jenes",
    "sowie", "wobei", "weshalb", "weshalb", "darunter", "darüber",
    "teilweise", "zeitweise", "gelegentlich", "manchmal",
    "stark", "stärker", "leicht", "schwer", "deutlich",
    "erste", "zweite", "dritte", "letzten", "letztem",
    "kurz", "lang", "länger", "längerem", "länge",
    "zunehmend", "abnehmend", "anhaltend", "intermittierend",
}

# Generic single words to skip even if long enough
GENERIC_WORDS = {
    "beschwerden", "schmerzen", "bereich", "körper", "stelle", "seite",
    "therapie", "behandlung", "diagnose", "anamnese", "befund",
    "zustand", "verlauf", "dauer", "jahre", "jahren", "monate",
    "monaten", "wochen", "tagen", "täglich", "chronisch",
    "aufenthalt", "erhoffe", "energie", "kraft", "wieder",
    "symptome", "symptomatik", "beschwerdbild", "krankheit",
    "erkrankung", "medikament", "medikamente", "medikation",
    "linderung", "verschlechterung", "verbesserung",
    "therapierelevante", "therapierelevant",
}

# Medical suffixes — term must contain at least one word ending with these
MEDICAL_SUFFIXES = (
    "itis", "algie", "algia", "ose", "pathie", "pathisch",
    "syndrom", "störung", "insuffizienz", "tinnitus", "schwindel",
    "neuropathie", "neuropathisch", "polyneuropath",
    "sklerose", "fibromyalgie", "migräne", "zystitis",
    "kolitis", "gastritis", "hepatitis", "thyreoiditis",
    "stenose", "arthrose", "arthritis", "bursitis", "tendinitis",
    "myalgie", "neuralgie", "lumbago", "radikulopathie",
    "lähmung", "parese", "plegie", "atrophie",
    "angiopathie", "retinopathie", "nephropathie",
    "dysmenorrhoe", "amenorrhoe", "endometriose",
    "dermatitis", "psoriasis", "ekzem",
    "schlafstörung", "erschöpfung", "erschöpfungs",
    "depression", "angststörung", "burnout",
    "schmerzsyndrom", "kopfschmerz", "rückenschmerz",
    "restless", "raynaud", "morbus", "spondylose",
    "spondylitis", "spondylolisthese", "diskushernie", "hernie",
    "zöliakie", "reizdarm", "colitis", "crohn",
    "hashimoto", "basedow", "hypothyreose", "hyperthyreose",
    "diabetes", "hypertonie", "hypotonie", "arrhythmie",
    "tachykardie", "bradykardie", "herzinsuffizienz",
    "osteoporose", "osteopenie", "rheuma", "lupus",
    "polyneuropathie", "karpaltunnel", "impingement",
    "ischias", "neuritis", "zervikalsyndrom", "lumbalsyndrom",
)

# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def extract_section(doc: Document) -> str:
    """Extract text between Derzeitige Beschwerden and Vormedikation."""
    paragraphs = [p.text.strip() for p in doc.paragraphs]
    collecting = False
    lines = []

    for para in paragraphs:
        lower = para.lower().rstrip(":")
        if not collecting:
            if START_HEADING in lower:
                collecting = True
        else:
            if END_HEADING in lower:
                break
            if para:
                lines.append(para)

    return " ".join(lines)


def split_sentences(text: str) -> list[str]:
    """Split text into sentence-like segments."""
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-zäöüß\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [t for t in text.split() if t not in STOPWORDS and len(t) >= 4]


# ---------------------------------------------------------------------------
# N-gram extraction
# ---------------------------------------------------------------------------

def extract_ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def has_medical_signal(term: str) -> bool:
    """Return True if term contains at least one medically significant word."""
    return any(suffix in term for suffix in MEDICAL_SUFFIXES)


def is_valid_term(term: str) -> bool:
    """Accept only clinically meaningful terms."""
    if len(term) < MIN_TERM_LEN:
        return False
    parts = term.split()
    # Reject if any part is a stopword (for single words)
    if len(parts) == 1:
        if term in GENERIC_WORDS or term in STOPWORDS:
            return False
    # Reject if all parts are noise
    if all(p in STOPWORDS or p in GENERIC_WORDS for p in parts):
        return False
    # Must contain at least one medical signal
    if not has_medical_signal(term):
        return False
    return True


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docx_files = sorted(DATASET_DIR.glob("*.docx"))
    total = len(docx_files)
    print(f"Processing {total} documents...")

    # term → set of doc names
    term_docs: dict[str, set] = defaultdict(set)
    # term → list of example sentences
    term_examples: dict[str, list[str]] = defaultdict(list)

    for i, filepath in enumerate(docx_files, 1):
        if i % 50 == 0:
            print(f"  {i}/{total}")
        try:
            doc = Document(filepath)
        except Exception:
            continue

        raw_section = extract_section(doc)
        if not raw_section:
            continue

        sentences = split_sentences(raw_section)
        cleaned   = clean(raw_section)
        tokens    = tokenize(cleaned)

        # Collect all candidate terms (1-4 grams)
        candidates: set[str] = set()
        for n in range(1, 5):
            for gram in extract_ngrams(tokens, n):
                if is_valid_term(gram):
                    candidates.add(gram)

        docname = filepath.name
        for term in candidates:
            term_docs[term].add(docname)

        # Store example sentences (up to MAX_EXAMPLES per term)
        for term in candidates:
            if len(term_examples[term]) < MAX_EXAMPLES:
                for sent in sentences:
                    if term in sent.lower():
                        if sent not in term_examples[term]:
                            term_examples[term].append(sent)
                            break

    print("Building results...")

    # Filter: rare terms only
    rows = []
    for term, docs in term_docs.items():
        count = len(docs)
        if MIN_DOCS <= count <= MAX_DOCS:
            rows.append({
                "term": term,
                "document_count": count,
                "percent": round(count / total * 100, 1),
            })

    df = pd.DataFrame(rows).sort_values("document_count").reset_index(drop=True)
    df.to_csv(OUTPUT_DIR / "rare_symptom_candidates.csv", index=False)
    print(f"Saved {len(df)} rare terms to outputs/rare_symptom_candidates.csv")

    # Examples output
    example_rows = []
    for _, row in df.iterrows():
        term = row["term"]
        examples = term_examples.get(term, [])[:MAX_EXAMPLES]
        example_rows.append({
            "term": term,
            "document_count": row["document_count"],
            "percent": row["percent"],
            "examples": " | ".join(examples),
        })

    df_ex = pd.DataFrame(example_rows).sort_values("document_count")
    df_ex.to_csv(OUTPUT_DIR / "rare_symptom_examples.csv", index=False)
    print(f"Saved examples to outputs/rare_symptom_examples.csv")


if __name__ == "__main__":
    main()
