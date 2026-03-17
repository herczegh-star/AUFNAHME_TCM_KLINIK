"""
auto_filter_review.py
---------------------
Auto-mark likely noise in cluster_candidates_review.csv.
Does NOT overwrite existing status values.
"""

import re
from pathlib import Path
import pandas as pd

INPUT  = Path("outputs/cluster_candidates_review.csv")
OUTPUT = Path("outputs/cluster_candidates_review_filtered.csv")

# Words that indicate noise / grammar fragments
NOISE_WORDS = {
    "hätte", "wäre", "wurde", "wurden", "seien", "geworden",
    "berichtet", "beschreibt", "handelt", "stellt", "stellen",
    "kurzgefasst", "gehabt", "bereits", "winter", "sommer",
    "herbst", "frühling", "vorliegenden", "unterlagen",
    "zusammenfassend", "hinaus", "erhoffe", "erfahre",
    "betrage", "bestehe", "würde", "würden", "welche",
    "zusammenhang", "hinsichtlich", "können", "genug",
    "zurückhaltend", "schnell", "meistens", "allem",
    "allen", "beeinträchtigt", "gestört", "treten",
}


def is_noise(term: str) -> bool:
    parts = term.split()

    # Too many words
    if len(parts) > 3:
        return True

    # Too long
    if len(term) > 40:
        return True

    # Contains numbers or digits
    if re.search(r"\d", term):
        return True

    # Contains noise words
    if any(p in NOISE_WORDS for p in parts):
        return True

    return False


def main():
    df = pd.read_csv(INPUT, encoding="utf-8")
    df["status"] = df["status"].fillna("")

    noise_count = 0
    for idx, row in df.iterrows():
        if str(row["status"]).strip():
            continue  # don't overwrite existing
        if is_noise(str(row["term"])):
            df.at[idx, "status"] = "NOISE_SUSPECT"
            noise_count += 1

    total     = len(df)
    remaining = total - noise_count

    df.to_csv(OUTPUT, index=False, encoding="utf-8")

    print(f"Total terms:         {total}")
    print(f"Noise suspects:      {noise_count}")
    print(f"Remaining candidates:{remaining}")
    print(f"\nSaved to {OUTPUT}")


if __name__ == "__main__":
    main()
