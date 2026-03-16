"""
symptom_analysis.py
-------------------
Analyse 650 DOCX medical reports and extract frequently occurring
medical terms and bigrams.

Output: outputs/symptom_candidates.csv
"""

import re
from collections import Counter
from pathlib import Path

import pandas as pd
from docx import Document

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "dataset" / "aufnahmeberichte"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "symptom_candidates.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# German stopwords (compact but practical set)
# ---------------------------------------------------------------------------

STOPWORDS = {
    "aber", "alle", "allem", "allen", "aller", "alles", "also", "andere",
    "anderen", "anderem", "anderer", "anderes", "anderm", "andern", "anderr",
    "anderes", "auch", "auf", "aus", "bei", "beim", "bin", "bis", "bisher",
    "bitte", "beide", "beiden", "da", "damit", "dann", "dass", "daher",
    "darum", "dazu", "dein", "deine", "dem", "den", "denn", "der", "des",
    "diese", "diesem", "diesen", "dieser", "dieses", "doch", "dort", "durch",
    "ein", "eine", "einem", "einen", "einer", "eines", "einige", "einiges",
    "einmal", "erst", "entweder", "etwa", "etwas", "euch", "falls", "fuer",
    "für", "gegen", "gemäß", "gibt", "haben", "hatte", "hatten", "hier",
    "hinter", "ihm", "ihn", "ihnen", "ihr", "ihre", "ihrem", "ihren",
    "ihrer", "ihres", "immer", "indem", "infolge", "inner", "ins", "irgend",
    "ist", "jede", "jedem", "jeden", "jeder", "jedes", "jedoch", "kann",
    "kein", "keine", "keinem", "keinen", "keiner", "keines", "können",
    "konnte", "machen", "mehr", "mein", "meine", "meinem", "meinen",
    "meiner", "meines", "mit", "muss", "nach", "nein", "nicht", "noch",
    "nun", "nur", "oder", "ohne", "per", "sein", "seine", "seinem", "seinen",
    "seiner", "seines", "seit", "sich", "sie", "sind", "so", "soll",
    "sollte", "sonst", "sowie", "später", "über", "um", "und", "uns",
    "unter", "sehr", "viel", "viele", "vielen", "vom", "von", "vor", "war",
    "waren", "was", "wegen", "weil", "weiter", "wenn", "werden", "wie",
    "wird", "wir", "wird", "wo", "wurde", "wurden", "zwar", "zwischen",
    "zum", "zur", "zuerst", "zunächst", "bereits", "beim", "wird", "hatte",
    "haben", "worden", "werden", "worden", "wurde", "wurden", "welche",
    "welchen", "welchem", "welcher", "welches", "dessen", "deren", "derer",
    "dies", "diesem", "diesen", "dieser", "dieses", "jetzt", "bisher",
    "hierzu", "hierbei", "insbesondere", "aufgrund", "sowie", "wobei",
    "dabei", "hierfür", "davon", "daran", "darauf", "darüber", "hierin",
    "allgemein", "allem", "allen", "ebenfalls", "entsprechend", "weiterhin",
    "gegeben", "gezeigt", "beschrieben", "berichtet", "angegeben",
    "bekannt", "zeigt", "zeigen", "ergibt", "erhalten", "erfolgt",
    "patientin", "patient", "patientinnen", "patienten",
    # document structure words
    "anamnese", "eigenanamnese", "familienanamnese", "sozialanamnese",
    "diagnosen", "diagnose", "diagnostik", "befund", "befunde",
    "vegetative", "allgemeine", "therapie", "therapien",
    "untersuchung", "untersuchungen", "behandlung", "behandlungen",
    "medikamente", "medikation", "vormedikation", "empfehlung",
    "empfehlungen", "zusammenfassung", "beurteilung", "verlauf",
    "vorstellung", "vorgeschichte", "krankengeschichte",
    "aufnahme", "entlassung", "konsultation", "erstvorstellung",
    "wiedervorstellung", "kontrolltermin", "aktuell", "aktueller",
    "aktuellen", "aktuelles", "derzeit", "derzeitige", "derzeitiger",
    "allgemeinzustand", "zustand", "zähne", "atemgeräusch",
    "beweglich", "tastbar", "gepflegtem", "gepflegter",
    "frei", "keine", "ergibt", "erhalten", "erfolgt",
    "abschnitte", "abschnitten", "abschnitt",
}

MIN_WORD_LENGTH = 4
MIN_DOC_PERCENT = 1.0


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(docx_path: Path) -> str:
    try:
        doc = Document(docx_path)
        return " ".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"  [WARN] Could not read {docx_path.name}: {e}")
        return ""


def tokenize(text: str) -> list[str]:
    text = text.lower()
    # unicode word chars — captures German umlauts correctly
    tokens = re.findall(r"\b\w{%d,}\b" % MIN_WORD_LENGTH, text)
    # keep only alphabetic tokens (no numbers, no underscores)
    tokens = [t for t in tokens if re.fullmatch(r"[^\W\d_]+", t, re.UNICODE)]
    return [t for t in tokens if t not in STOPWORDS]


def make_bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyse():
    files = sorted(INPUT_DIR.glob("*.docx"))
    total = len(files)
    print(f"Found {total} documents in {INPUT_DIR}")

    unigram_docs: Counter = Counter()
    bigram_docs: Counter = Counter()

    for i, path in enumerate(files, 1):
        if i % 50 == 0 or i == total:
            print(f"  Processing {i}/{total} ...")

        text = extract_text(path)
        tokens = tokenize(text)
        bigrams = make_bigrams(tokens)

        # count each term once per document
        for term in set(tokens):
            unigram_docs[term] += 1
        for term in set(bigrams):
            bigram_docs[term] += 1

    # merge
    all_terms: dict[str, int] = {}
    all_terms.update(unigram_docs)
    all_terms.update(bigram_docs)

    min_docs = max(1, int(total * MIN_DOC_PERCENT / 100))

    rows = [
        {
            "term": term,
            "document_count": count,
            "percent": round(count / total * 100, 1),
        }
        for term, count in all_terms.items()
        if count >= min_docs
    ]

    df = pd.DataFrame(rows).sort_values("percent", ascending=False).reset_index(drop=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nDone. {len(df)} terms saved to {OUTPUT_FILE}")
    print(df.head(20).to_string(index=False))


if __name__ == "__main__":
    analyse()
