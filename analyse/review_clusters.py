"""
review_clusters.py
------------------
Build a manual clinical review table from symptom clusters.

- Re-uses cached embeddings if available (outputs/embeddings_cache.npz)
- Outputs 20 representative phrases per cluster
- Auto-proposes a clinical label based on keywords
- Saves outputs/cluster_review.csv

Sort: percent_of_documents descending.
"""

import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from sentence_transformers import SentenceTransformer
import hdbscan

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR    = Path(__file__).parent.parent
INPUT_DIR   = BASE_DIR / "dataset" / "aufnahmeberichte"
OUTPUT_DIR  = BASE_DIR / "outputs"
CACHE_FILE  = OUTPUT_DIR / "embeddings_cache.npz"
OUTPUT_FILE = OUTPUT_DIR / "cluster_review.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Config (must match cluster_analysis.py)
# ---------------------------------------------------------------------------

SECTION_START = re.compile(r"derzeitige\s+beschwerden", re.IGNORECASE)
SECTION_END   = re.compile(r"vormedikation\s*:?", re.IGNORECASE)

MODEL_NAME               = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_SEG_LEN              = 20
HDBSCAN_MIN_CLUSTER_SIZE = 8
HDBSCAN_MIN_SAMPLES      = 3
TOP_PHRASES              = 20

# ---------------------------------------------------------------------------
# Auto-label rules  (checked in order, first match wins)
# ---------------------------------------------------------------------------

LABEL_RULES: list[tuple[str, list[str]]] = [
    ("Boilerplate – Vorgeschichte",    ["vorgeschichte", "als bekannt voraussetzen", "verweisen auf"]),
    ("Boilerplate – Erwartungen",      ["erhoffe", "aufenthalt erhoffe"]),
    ("Erschöpfung / Müdigkeit",        ["erschöpf", "müdigk", "müde", "fatigue", "energiemangel"]),
    ("Schlafstörungen",                ["schlafstörung", "einschlaf", "durchschlaf", "schlaf sei"]),
    ("Stimmung / Depression",          ["stimmung", "gedrückt", "depressiv", "niedergeschlagen", "antriebslos"]),
    ("Angst / Panik",                  ["angst", "panik", "unruhig", "innere unruhe"]),
    ("Tinnitus",                       ["tinnitus"]),
    ("Schwindel",                      ["schwindel"]),
    ("Kopfschmerzen / Migräne",        ["kopfschmerz", "migräne", "hemikranie"]),
    ("LWS-Beschwerden",                ["lws", "lendenwirbel", "lumbal", "kreuzschmerz"]),
    ("HWS-Beschwerden",                ["hws", "halswirbel", "cervikal", "nackenschmerz", "nacken"]),
    ("Schulter / Arm",                 ["schulter", "schulterblatt", "arm schmerz"]),
    ("Knie / Hüfte / Gelenk",         ["knie", "hüfte", "gelenk", "koxalgie", "gonalgie"]),
    ("Schmerzen – Charakter",          ["ziehend", "stechend", "pochend", "dumpf", "brennend"]),
    ("Reizdarm / GI",                  ["darm", "bauch", "blähung", "völlegefühl", "verstopf", "durchfall", "übelkeit", "reizdarm"]),
    ("Herzrasen / Palpitationen",      ["herzrasen", "palpitation", "herzklopfen"]),
    ("Polyneuropathie",                ["kribbeln", "taubheitsgefühl", "polyneuropath", "missempfindung"]),
    ("Belastbarkeit",                  ["belastbarkeit", "belastungsgrenze", "leistungsfähigkeit"]),
    ("Symptomverlauf / Verschlechterung", ["verschlechter", "zugespitzt", "zunehmend", "progredient"]),
]


def propose_label(phrases: list[str]) -> str:
    combined = " ".join(phrases).lower()
    for label, keywords in LABEL_RULES:
        if any(kw in combined for kw in keywords):
            return label
    return "Sonstige / unbekannt"


# ---------------------------------------------------------------------------
# Section extraction + segmentation
# ---------------------------------------------------------------------------

def extract_section(path: Path) -> str:
    try:
        doc = Document(path)
    except Exception:
        return ""
    collecting, lines = False, []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not collecting:
            if SECTION_START.search(text):
                collecting = True
            continue
        if SECTION_END.search(text):
            break
        if text:
            lines.append(text)
    return " ".join(lines)


def split_sentences(text: str) -> list[str]:
    segments = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", text)
    result: list[str] = []
    for seg in segments:
        for part in re.split(r";\s*", seg):
            part = part.strip()
            if len(part) >= MIN_SEG_LEN:
                result.append(part)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    files = sorted(INPUT_DIR.glob("*.docx"))
    total_docs = len(files)
    print(f"Found {total_docs} documents")

    # 1. Extract segments
    segments: list[str] = []
    seg_to_doc: list[str] = []

    for i, path in enumerate(files, 1):
        if i % 50 == 0 or i == total_docs:
            print(f"  Extracting {i}/{total_docs} ...")
        text = extract_section(path)
        for s in split_sentences(text):
            segments.append(s)
            seg_to_doc.append(path.name)

    print(f"  Total segments: {len(segments)}")

    # 2. Embeddings (with cache)
    if CACHE_FILE.exists():
        print(f"\nLoading cached embeddings from {CACHE_FILE}")
        data = np.load(CACHE_FILE, allow_pickle=True)
        embeddings = data["embeddings"]
        cached_segs = list(data["segments"])
        if cached_segs == segments:
            print("  Cache matches current segments — using cache.")
        else:
            print("  Cache mismatch — recomputing embeddings.")
            embeddings = _compute_embeddings(segments)
            _save_cache(segments, embeddings)
    else:
        print(f"\nNo cache found — computing embeddings with {MODEL_NAME}")
        embeddings = _compute_embeddings(segments)
        _save_cache(segments, embeddings)

    # 3. Cluster
    print("\nClustering ...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(embeddings)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    print(f"  {n_clusters} clusters, {(labels == -1).sum()} noise segments")

    # 4. Aggregate
    cluster_segs: dict[int, list[str]] = defaultdict(list)
    cluster_docs: dict[int, set]       = defaultdict(set)
    cluster_embs: dict[int, list]      = defaultdict(list)

    for seg, doc_name, label, emb in zip(segments, seg_to_doc, labels, embeddings):
        if label == -1:
            continue
        cluster_segs[label].append(seg)
        cluster_docs[label].add(doc_name)
        cluster_embs[label].append(emb)

    # 5. Build review table
    rows: list[dict] = []

    for label in sorted(cluster_segs.keys()):
        segs  = cluster_segs[label]
        docs  = cluster_docs[label]
        embs  = np.array(cluster_embs[label])
        centroid = embs.mean(axis=0)
        dists    = np.linalg.norm(embs - centroid, axis=1)
        top_idx  = dists.argsort()[:TOP_PHRASES]

        # deduplicate while preserving order
        seen: set[str] = set()
        rep: list[str] = []
        for idx in top_idx:
            s = segs[idx]
            if s not in seen:
                seen.add(s)
                rep.append(s)

        proposed = propose_label(rep)

        rows.append({
            "cluster_id":            label,
            "proposed_label":        proposed,
            "segment_count":         len(segs),
            "document_count":        len(docs),
            "percent_of_documents":  round(len(docs) / total_docs * 100, 1),
            "representative_phrases": "\n---\n".join(rep),
        })

    df = (
        pd.DataFrame(rows)
        .sort_values("percent_of_documents", ascending=False)
        .reset_index(drop=True)
    )
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nDone. {len(df)} clusters saved to {OUTPUT_FILE}")
    print(df[["cluster_id", "proposed_label", "document_count",
              "percent_of_documents"]].head(25).to_string(index=False))


def _compute_embeddings(segments: list[str]) -> np.ndarray:
    model = SentenceTransformer(MODEL_NAME)
    return model.encode(segments, batch_size=64, show_progress_bar=True,
                        convert_to_numpy=True)


def _save_cache(segments: list[str], embeddings: np.ndarray) -> None:
    np.savez_compressed(CACHE_FILE,
                        embeddings=embeddings,
                        segments=np.array(segments, dtype=object))
    print(f"  Embeddings cached to {CACHE_FILE}")


if __name__ == "__main__":
    main()
