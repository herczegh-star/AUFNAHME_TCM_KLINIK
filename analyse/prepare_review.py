"""
prepare_review.py
-----------------
Prepare manual review file from cluster_candidates.csv.
"""

from pathlib import Path
import pandas as pd

INPUT  = Path("outputs/cluster_candidates.csv")
OUTPUT = Path("outputs/cluster_candidates_review.csv")

df = pd.read_csv(INPUT, encoding="utf-8")

df = df.sort_values(
    ["document_count", "term"],
    ascending=[False, True]
).reset_index(drop=True)

df["status"]       = ""
df["ziel_cluster"] = ""
df["kommentar"]    = ""

df = df[["term", "document_count", "percent", "status", "ziel_cluster", "kommentar"]]
df.to_csv(OUTPUT, index=False, encoding="utf-8")
print(f"Saved {len(df)} terms to {OUTPUT}")
