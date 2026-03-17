"""
cluster_candidates.py
---------------------
Filter rare_symptom_examples.csv to extract only clinically
meaningful symptom / diagnosis candidates.

Output:
  outputs/cluster_candidates.csv
"""

import re
from pathlib import Path

import pandas as pd

INPUT_FILE  = Path("outputs/rare_symptom_examples.csv")
OUTPUT_FILE = Path("outputs/cluster_candidates.csv")

# ---------------------------------------------------------------------------
# Noise indicators — if ANY of these appear in a term, reject it
# ---------------------------------------------------------------------------

NOISE_WORDS = {
    # verbs
    "hätte", "habe", "hatte", "haben", "wurde", "werden", "worden",
    "seien", "wäre", "würde", "würden", "werde", "solle", "könne",
    "zeigt", "zeige", "zeigen", "stellt", "stellen", "berichtet",
    "beschreibt", "erfahre", "erhoffe", "betrage", "bestehe",
    "hinaus", "kurzgefasst", "zusammenfassend",
    # pronouns / articles
    "sein", "seine", "seinen", "seiner", "ihren", "ihrer", "ihre",
    "diesem", "dieser", "dieses", "diese", "einen", "einem",
    "welche", "welchen", "welcher",
    # prepositions / conjunctions
    "sowie", "wobei", "weshalb", "darunter", "darüber", "hinaus",
    "winter", "sommer", "herbst", "frühling",
    # administrative
    "unterlagen", "vorliegenden", "handelt", "fortgeschrittene",
    "diagnose", "befund", "anamnese", "kurzgefasst",
    # generic descriptors (not diagnoses)
    "nahezu", "hinsichtlich", "sinne", "muster", "formen",
    "begleitet", "monatlich", "dreimal", "zwölf",
    # body parts that alone are not diagnoses
    "schulter", "knie", "hüfte", "wirbel",
}

# German verb endings — terms ending with these are likely verbs/fragments
VERB_ENDINGS = (
    "end", "end", "end",  # present participle in isolation is ok (ziehend)
)

# Medical suffixes — term must contain at least one
MEDICAL_SUFFIXES = (
    "itis", "algie", "algia", "ose", "pathie", "pathisch",
    "syndrom", "störung", "insuffizienz", "tinnitus",
    "neuropathie", "neuropathisch", "polyneuropath",
    "sklerose", "fibromyalgie", "migräne", "zystitis",
    "kolitis", "gastritis", "hepatitis", "thyreoiditis",
    "stenose", "arthrose", "arthritis", "bursitis", "tendinitis",
    "myalgie", "neuralgie", "lumbago", "radikulopathie",
    "lähmung", "parese", "plegie", "atrophie",
    "angiopathie", "retinopathie", "nephropathie",
    "dysmenorrhoe", "amenorrhoe", "endometriose",
    "dermatitis", "psoriasis", "ekzem",
    "schlafstörung", "schlafapnoe", "erschöpfung",
    "depression", "angststörung", "burnout",
    "schmerzsyndrom", "kopfschmerz", "rückenschmerz",
    "restless", "raynaud", "morbus", "spondylose",
    "spondylitis", "spondylolisthese", "diskushernie", "hernie",
    "zöliakie", "reizdarm", "colitis", "crohn",
    "hashimoto", "basedow", "hypothyreose", "hyperthyreose",
    "diabetes", "hypertonie", "hypotonie", "arrhythmie",
    "tachykardie", "bradykardie", "herzinsuffizienz",
    "osteoporose", "osteopenie", "rheuma", "lupus",
    "karpaltunnel", "impingement",
    "ischias", "neuritis", "zervikalsyndrom", "lumbalsyndrom",
    "hyperkyphose", "kyphose", "skoliose", "lordose",
    "osteochondrose", "osteochondrosen", "ostechondrose",
    "cephalgie", "cephalgien", "lumboischialgie",
    "polyneuropathie", "mononeuropathie",
    "koxarthrose", "gonarthrose", "rhizarthrose",
    "rhinitis", "sinusitis", "pharyngitis",
    "apnoe", "schlafapnoe",
    "merkfähigkeitsstörung", "konzentrationsstörung",
    "erschöpfungssyndrom", "erschöpfungsgefühl",
    "fingerpolyarthrose", "polyarthrose", "polyarthritis",
    "spannungskopfschmerz", "migräneattacken",
    "einschlafstörung", "durchschlafstörung",
    "neurodermitis", "urtikaria",
    "zervikozephales", "zervikozephale",
)

MAX_WORDS = 4  # reject phrases longer than this


def has_medical_signal(term: str) -> bool:
    return any(suffix in term for suffix in MEDICAL_SUFFIXES)


def is_clean_term(term: str) -> bool:
    """Return True if the term looks like a medical symptom/diagnosis."""
    parts = term.split()

    # Reject overly long phrases
    if len(parts) > MAX_WORDS:
        return False

    # Reject if any noise word is present
    if any(p in NOISE_WORDS for p in parts):
        return False

    # Must have medical signal
    if not has_medical_signal(term):
        return False

    return True


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep the most specific term when a shorter version is a substring.
    E.g. keep 'polyneuropathie' over 'zunehmende polyneuropathie' if
    the counts are the same, but prefer multi-word if more specific.
    Simple approach: for each group of terms sharing a medical core,
    keep the one with highest document_count.
    """
    # Group terms that share the same medical core word
    # For now: just deduplicate exact substrings — keep shorter clean terms
    # and drop longer ones that are just wrappers around the same term
    terms = df["term"].tolist()
    to_drop = set()

    for i, t1 in enumerate(terms):
        for j, t2 in enumerate(terms):
            if i == j:
                continue
            # if t1 is a substring of t2 AND t2 has same or lower count → drop t2
            if t1 in t2 and t1 != t2:
                count1 = df.iloc[i]["document_count"]
                count2 = df.iloc[j]["document_count"]
                if count2 <= count1:
                    to_drop.add(j)

    keep_idx = [i for i in range(len(df)) if i not in to_drop]
    return df.iloc[keep_idx].reset_index(drop=True)


def main():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    # Keep unique terms with their counts
    df_terms = (
        df[["term", "document_count", "percent"]]
        .drop_duplicates(subset="term")
        .copy()
    )

    # Apply clinical filter
    mask = df_terms["term"].apply(is_clean_term)
    df_clean = df_terms[mask].copy()

    # Deduplicate overlapping terms
    df_clean = df_clean.sort_values("document_count", ascending=False).reset_index(drop=True)
    df_clean = deduplicate(df_clean)

    # Sort descending
    df_clean = df_clean.sort_values("document_count", ascending=False).reset_index(drop=True)

    # Save
    df_clean.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"Saved {len(df_clean)} candidates to {OUTPUT_FILE}\n")

    # Print top 50
    print("Top 50 cluster candidates:")
    print("-" * 50)
    print(df_clean.head(50).to_string(index=False))


if __name__ == "__main__":
    main()
