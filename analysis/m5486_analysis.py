"""
m5486_analysis.py
-----------------
Steps 1–6 for M54.86 corpus analysis.

  Step 1: load corpus
  Step 2: technical cleanup + dedup
  Step 3: embedding + K-means clustering
  Step 4: recurring segment analysis per cluster
  Step 5: Claude API archetype curation
  Step 6: coverage estimate

Outputs:
  outputs/m5486_cluster_report.md
  outputs/m5486_cluster_examples.json
  outputs/lws_patterns_generated.md
"""
from __future__ import annotations

import json
import os
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_JSONL      = Path("outputs/database001_records.jsonl")
_OUT_DIR    = Path("outputs")
_ICD        = "M54.86"
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_K_RANGE    = range(3, 7)   # try k=3..6, pick best silhouette


# ---------------------------------------------------------------------------
# Step 1+2: Load and clean corpus
# ---------------------------------------------------------------------------

def load_corpus() -> list[dict]:
    with open(_JSONL, encoding="utf-8") as fh:
        all_recs = [json.loads(l) for l in fh]

    m_recs = [r for r in all_recs if r["icd_code"] == _ICD]

    # Deduplicate by text_block — keep first occurrence per unique text
    seen: dict[str, dict] = {}
    for r in m_recs:
        tb = _clean(r["text_block"])
        if tb not in seen:
            seen[tb] = {**r, "text_block": tb}

    corpus = list(seen.values())
    print(f"[Step 1+2] M54.86 records: {len(m_recs)} -> unique texts: {len(corpus)}")
    return corpus


def _clean(text: str) -> str:
    """Technical cleanup only: collapse whitespace, strip."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Step 3: Embed + cluster
# ---------------------------------------------------------------------------

def embed_and_cluster(corpus: list[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    texts = [r["text_block"] for r in corpus]

    print(f"[Step 3] Loading embedding model: {_MODEL_NAME}")
    model = SentenceTransformer(_MODEL_NAME)
    print(f"[Step 3] Embedding {len(texts)} texts...")
    embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
    embeddings = normalize(embeddings)

    # Choose k by silhouette score
    best_k, best_score, best_labels = 3, -1.0, None
    for k in _K_RANGE:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(embeddings)
        score  = silhouette_score(embeddings, labels)
        print(f"  k={k}  silhouette={score:.4f}")
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels

    print(f"[Step 3] Best k={best_k}  silhouette={best_score:.4f}")
    return embeddings, best_labels, best_k


# ---------------------------------------------------------------------------
# Step 4: Recurring segment analysis
# ---------------------------------------------------------------------------

# Simple German keyword sets for clinical dimensions
_SEGMENT_PATTERNS: dict[str, list[str]] = {
    "chronicity":    [r'chronisch', r'jahrelang', r'seit Jahren', r'seit \w+ Jahren',
                      r'rezidivierend', r'wiederkehrend', r'persistierend', r'anhaltend'],
    "radiation":     [r'Ausstrahlung', r'strahlt', r'ausstrahlend', r'Bein', r'Gesäß',
                      r'radikulär', r'Ischialgie', r'ischialgiform'],
    "character":     [r'ziehend', r'stechend', r'dumpf', r'drückend', r'brennend',
                      r'krampfartig', r'pulsierend'],
    "aggravating":   [r'Sitzen', r'Stehen', r'Gehen', r'Belastung', r'Bücken',
                      r'Treppensteigen', r'Bewegung', r'belastungsabhängig'],
    "relieving":     [r'Wärme', r'Ruhe', r'Liegen', r'Entlastung', r'Massage',
                      r'manuelle Therapie', r'Physiotherapie'],
    "surgery_bsv":   [r'Operation', r'operiert', r'Z\.n\. OP', r'Bandscheibe',
                      r'Bandscheibenvorfall', r'BSV', r'Prolaps', r'Nukleotomie',
                      r'Dekompression', r'Spondylodese'],
    "neuro":         [r'Kribbeln', r'Kribbelparästhesien', r'Taubheit', r'Taubheitsgefühl',
                      r'Parästhesien', r'motorisch', r'Sensibilitätsstörung', r'Lähmung'],
    "functional":    [r'Sitztoleranz', r'Gehstrecke', r'eingeschränkt', r'Bewegungseinschränkung',
                      r'Arbeitsunfähigkeit', r'beeinträchtigt', r'Alltag'],
}


def analyse_segments(texts: list[str]) -> dict[str, float]:
    """Return fraction of texts containing each segment type."""
    n = len(texts)
    result = {}
    for dim, patterns in _SEGMENT_PATTERNS.items():
        regex = re.compile('|'.join(patterns), re.IGNORECASE)
        hit = sum(1 for t in texts if regex.search(t))
        result[dim] = round(hit / n, 2)
    return result


# ---------------------------------------------------------------------------
# Step 5: Claude archetype curation
# ---------------------------------------------------------------------------

def curate_with_claude(
    cluster_summaries: list[dict],
    k: int,
) -> str:
    """
    Send cluster summaries to Claude and request 2-4 LWS archetypes.
    Returns raw model output (German clinical patterns).
    """
    import anthropic

    client = anthropic.Anthropic()

    # Build prompt
    cluster_block = ""
    for cs in cluster_summaries:
        cluster_block += f"\n--- CLUSTER {cs['id']} (n={cs['size']}) ---\n"
        cluster_block += f"Dominant features: {cs['features']}\n"
        cluster_block += "Representative texts (first 300 chars each):\n"
        for i, ex in enumerate(cs['examples'][:5], 1):
            cluster_block += f"  [{i}] {ex[:300]}\n"

    prompt = textwrap.dedent(f"""
    You are a clinical documentation expert specializing in German-language TCM/orthopedic intake reports.

    Below are {k} clusters automatically derived from {sum(cs['size'] for cs in cluster_summaries)} real patient records,
    all carrying ICD M54.86 (LWS-Syndrom).

    {cluster_block}

    TASK:
    Derive 2–3 final representative LWS archetypes (max 4 only if truly necessary).
    Name them LWS1, LWS2, LWS3 (and optionally LWS4).

    For each archetype provide:
    1. final_text: a compact 3–4 line German clinical summary text, Verdichtungsstil,
       suitable for direct use in a TCM intake template.
       - Nominalized style, no full sentences with verb conjugations where possible
       - Include: pain character, location, chronicity/course, aggravating/relieving factors
       - Include radiation/neuro only if clearly supported by the cluster data
    2. source_clusters: which cluster IDs this archetype is primarily derived from
    3. differentiator: one short phrase saying what makes this pattern distinct
    4. patient_fit: one short phrase describing the typical patient

    STRICT RULES:
    - Only include clinical content that appears in the source texts
    - No invented diagnoses or speculation
    - No poetic language
    - German language only for final_text
    - Keep final_text under 500 characters

    OUTPUT FORMAT (JSON array, nothing else):
    [
      {{
        "id": "LWS1",
        "final_text": "...",
        "source_clusters": [0, 1],
        "differentiator": "...",
        "patient_fit": "..."
      }},
      ...
    ]
    """).strip()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_cluster_report(
    corpus: list[dict],
    labels: np.ndarray,
    k: int,
    cluster_summaries: list[dict],
    output_path: Path,
) -> None:
    lines = [
        "# M54.86 Cluster Report",
        "",
        f"**ICD:** M54.86 (LWS-Syndrom)  ",
        f"**Total unique texts:** {len(corpus)}  ",
        f"**Clusters (best k):** {k}",
        "",
    ]

    for cs in cluster_summaries:
        lines += [
            f"## Cluster {cs['id']}  (n={cs['size']})",
            "",
            f"**Recurring features (fraction of texts):**",
            "",
        ]
        for dim, frac in sorted(cs['features'].items(), key=lambda x: -x[1]):
            bar = "#" * int(frac * 20)
            lines.append(f"  {dim:15} {frac:.0%}  {bar}")
        lines += [
            "",
            "**5 representative texts (excerpt):**",
            "",
        ]
        for i, ex in enumerate(cs['examples'][:5], 1):
            excerpt = ex[:400].replace('\n', ' ')
            lines.append(f"**[{i}]** {excerpt}...")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_cluster_examples(
    corpus: list[dict],
    labels: np.ndarray,
    k: int,
    output_path: Path,
) -> None:
    clusters: dict[int, list[dict]] = {i: [] for i in range(k)}
    for rec, label in zip(corpus, labels):
        clusters[int(label)].append(rec)

    out = []
    for cid in range(k):
        members = clusters[cid]
        out.append({
            "cluster_id": cid,
            "size": len(members),
            "examples": [
                {
                    "source_case_id": r["source_case_id"],
                    "text_block": r["text_block"][:500],
                }
                for r in members[:10]
            ],
        })

    output_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_patterns(archetypes_json: str, cluster_summaries: list[dict], output_path: Path) -> None:
    # Parse JSON from model output (may have markdown fence)
    raw = archetypes_json.strip()
    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        archetypes = json.loads(raw)
    except json.JSONDecodeError:
        archetypes = []

    lines = [
        "# LWS Patterns — AI-Derived from M54.86 Corpus",
        "",
        f"**Source:** {sum(cs['size'] for cs in cluster_summaries)} unique M54.86 clinical texts",
        f"**Method:** sentence-transformer embedding → K-means → Claude Opus 4.6 curation",
        "",
        "---",
        "",
    ]

    for arch in archetypes:
        pid   = arch.get("id", "?")
        text  = arch.get("final_text", "")
        srcs  = arch.get("source_clusters", [])
        diff  = arch.get("differentiator", "")
        fit   = arch.get("patient_fit", "")

        lines += [
            f"## {pid}",
            "",
            "**Final text:**",
            "",
            f"> {text}",
            "",
            f"**Source clusters:** {srcs}  ",
            f"**Differentiator:** {diff}  ",
            f"**Patient fit:** {fit}",
            "",
            "---",
            "",
        ]

    # Coverage section placeholder
    lines += [
        "## Coverage Estimate",
        "",
        "*(See Step 6 output in cluster report)*",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return archetypes


# ---------------------------------------------------------------------------
# Step 6: Coverage estimate
# ---------------------------------------------------------------------------

def coverage_estimate(
    corpus: list[dict],
    labels: np.ndarray,
    archetypes: list[dict],
    cluster_summaries: list[dict],
) -> dict:
    """
    Estimate how many source texts are 'covered' by each archetype.
    An archetype covers a cluster if that cluster_id is in source_clusters.
    """
    covered_clusters: set[int] = set()
    for arch in archetypes:
        for cid in arch.get("source_clusters", []):
            covered_clusters.add(int(cid))

    covered = sum(1 for lbl in labels if int(lbl) in covered_clusters)
    total   = len(labels)
    outlier_clusters = set(range(len(cluster_summaries))) - covered_clusters

    return {
        "total_texts": total,
        "covered": covered,
        "coverage_pct": round(covered / total * 100, 1),
        "outlier_clusters": sorted(outlier_clusters),
        "outlier_count": sum(
            cs["size"] for cs in cluster_summaries
            if cs["id"] in outlier_clusters
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _OUT_DIR.mkdir(exist_ok=True)

    # Steps 1+2
    corpus = load_corpus()

    # Step 3
    embeddings, labels, k = embed_and_cluster(corpus)

    # Gather cluster data
    cluster_summaries = []
    for cid in range(k):
        mask  = labels == cid
        texts = [corpus[i]["text_block"] for i in range(len(corpus)) if mask[i]]
        feats = analyse_segments(texts)

        # Pick 5 examples: prefer texts with most feature hits
        def feature_score(t: str) -> int:
            return sum(
                1 for patterns in _SEGMENT_PATTERNS.values()
                if re.search('|'.join(patterns), t, re.IGNORECASE)
            )

        sorted_texts = sorted(texts, key=feature_score, reverse=True)
        cluster_summaries.append({
            "id": cid,
            "size": int(mask.sum()),
            "features": feats,
            "examples": sorted_texts[:10],
        })
        print(f"  Cluster {cid}: n={mask.sum()}, top features: "
              + ", ".join(f"{k}={v}" for k, v in sorted(feats.items(), key=lambda x: -x[1])[:4]))

    # Write cluster outputs
    write_cluster_report(
        corpus, labels, k, cluster_summaries,
        _OUT_DIR / "m5486_cluster_report.md",
    )
    write_cluster_examples(
        corpus, labels, k,
        _OUT_DIR / "m5486_cluster_examples.json",
    )
    print(f"[Step 3+4] Cluster files written.")

    # Step 5: Claude curation
    print("[Step 5] Calling Claude for archetype curation...")
    raw_output = curate_with_claude(cluster_summaries, k)
    print("[Step 5] Claude response received.")

    archetypes = write_patterns(
        raw_output, cluster_summaries,
        _OUT_DIR / "lws_patterns_generated.md",
    )
    print(f"[Step 5] Patterns written: {len(archetypes)} archetypes.")

    # Step 6: Coverage
    cov = coverage_estimate(corpus, labels, archetypes, cluster_summaries)
    print(f"[Step 6] Coverage: {cov['covered']}/{cov['total_texts']} "
          f"({cov['coverage_pct']}%)  "
          f"outlier clusters: {cov['outlier_clusters']}")

    # Append coverage to patterns file
    patterns_path = _OUT_DIR / "lws_patterns_generated.md"
    existing = patterns_path.read_text(encoding="utf-8")
    cov_block = "\n".join([
        "## Coverage Estimate",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total unique M54.86 texts | {cov['total_texts']} |",
        f"| Texts covered by archetypes | {cov['covered']} ({cov['coverage_pct']}%) |",
        f"| Outlier cluster(s) | {cov['outlier_clusters']} |",
        f"| Outlier text count | {cov['outlier_count']} |",
        "",
    ])
    patterns_path.write_text(
        existing.replace("*(See Step 6 output in cluster report)*\n", cov_block),
        encoding="utf-8",
    )

    print()
    print("Done.")
    print(f"  outputs/m5486_cluster_report.md")
    print(f"  outputs/m5486_cluster_examples.json")
    print(f"  outputs/lws_patterns_generated.md")


if __name__ == "__main__":
    main()
