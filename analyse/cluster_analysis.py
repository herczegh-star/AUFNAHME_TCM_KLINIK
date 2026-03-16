"""
cluster_analysis.py
-------------------
Cluster recurring symptom / complaint segments from "Derzeitige Beschwerden"
sections across 650 DOCX medical reports using sentence embeddings + HDBSCAN.

Output: outputs/symptom_clusters.csv
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

BASE_DIR   = Path(__file__).parent.parent
INPUT_DIR  = BASE_DIR / "dataset" / "aufnahmeberichte"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "symptom_clusters.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SECTION_START = re.compile(r"derzeitige\s+beschwerden", re.IGNORECASE)
SECTION_END   = re.compile(r"vormedikation\s*:?", re.IGNORECASE)

MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_SEG_LEN = 20   # minimum characters for a segment to be included
HDBSCAN_MIN_CLUSTER_SIZE = 8
HDBSCAN_MIN_SAMPLES      = 3
TOP_PHRASES_PER_CLUSTER  = 5

# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def extract_section(path: Path) -> str:
    try:
        doc = Document(path)
    except Exception as e:
        print(f"  [WARN] {path.name}: {e}")
        return ""

    collecting = False
    lines: list[str] = []

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


# ---------------------------------------------------------------------------
# Sentence segmentation
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    """Split text into sentence-like segments."""
    # split on period/exclamation/question mark followed by space + capital
    segments = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", text)
    # also split on semicolons if the part is long enough
    result: list[str] = []
    for seg in segments:
        parts = re.split(r";\s*", seg)
        result.extend(p.strip() for p in parts if len(p.strip()) >= MIN_SEG_LEN)
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
    seg_to_doc: list[str] = []   # which file each segment came from
    empty = 0

    for i, path in enumerate(files, 1):
        if i % 50 == 0 or i == total_docs:
            print(f"  Extracting {i}/{total_docs} ...")

        text = extract_section(path)
        if not text.strip():
            empty += 1
            continue

        segs = split_sentences(text)
        for s in segs:
            segments.append(s)
            seg_to_doc.append(path.name)

    print(f"\n  Extracted {len(segments)} segments from {total_docs - empty} docs "
          f"({empty} docs had no matching section)")

    # 2. Compute embeddings
    print(f"\nLoading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("Computing embeddings ...")
    embeddings = model.encode(segments, batch_size=64, show_progress_bar=True,
                              convert_to_numpy=True)

    # 3. Cluster
    print("\nClustering ...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(embeddings)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise    = (labels == -1).sum()
    print(f"  Found {n_clusters} clusters, {n_noise} noise segments")

    # 4. Aggregate cluster statistics
    cluster_segs: dict[int, list[str]]  = defaultdict(list)
    cluster_docs: dict[int, set]        = defaultdict(set)

    for seg, doc_name, label in zip(segments, seg_to_doc, labels):
        if label == -1:
            continue
        cluster_segs[label].append(seg)
        cluster_docs[label].add(doc_name)

    # 5. Pick representative phrases per cluster
    #    — the segments whose embedding is closest to the cluster centroid
    rows: list[dict] = []

    for label in sorted(cluster_segs.keys()):
        segs  = cluster_segs[label]
        docs  = cluster_docs[label]
        mask  = labels == label
        embs  = embeddings[mask]
        centroid = embs.mean(axis=0)

        dists = np.linalg.norm(embs - centroid, axis=1)
        top_idx = dists.argsort()[:TOP_PHRASES_PER_CLUSTER]
        rep_phrases = [segs[i] for i in top_idx]

        rows.append({
            "cluster_id":         label,
            "segment_count":      len(segs),
            "document_count":     len(docs),
            "percent":            round(len(docs) / total_docs * 100, 1),
            "representative_phrases": " | ".join(rep_phrases),
        })

    df = (
        pd.DataFrame(rows)
        .sort_values("document_count", ascending=False)
        .reset_index(drop=True)
    )
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nDone. {len(df)} clusters saved to {OUTPUT_FILE}")
    print(df[["cluster_id", "document_count", "percent",
              "representative_phrases"]].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
