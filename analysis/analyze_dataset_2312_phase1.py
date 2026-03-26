import re
import csv
import json
from pathlib import Path
from collections import defaultdict

# ==============================
# PATHS
# ==============================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR  = PROJECT_ROOT / "dataset" / "aufnahmeberichte_2312_"
OUTPUT_DIR   = PROJECT_ROOT / "analysis" / "output" / "analysis_output_phase1"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# EXCLUDED DIAGNOSES
# Diagnoses already covered by the template library — excluded from unique outputs only.
# Raw outputs (diagnosis_candidates_raw, diagnosis_frequency_*) remain unchanged.
# Matching is case-insensitive, exact string after clean_diagnosis().
# ==============================

EXCLUDED_DIAGNOSES: set[str] = {
    # top 20 by frequency — already covered by template library
    "arterielle hypertonie",
    "chronisches müdigkeitssyndrom",
    "lws-syndrom",
    "erschöpfungssyndrom",
    "hws-syndrom",
    "schlafstörungen",
    "ws-syndrom",
    "spannungskopfschmerzen",
    "fibromyalgie",
    "hypothyreose",
    "reizdarmsyndrom",
    "nichtorganische insomnie",
    "tinnitus aurium",
    "kopfschmerzen",
    "hashimoto thyreoiditis",
    "migräne",
    "tinnitus aurium bds.",
    "asthma bronchiale",
    "post-covid-19-syndrom",
    # previously excluded
    "allergisches asthma bronchiale",
}

# Diagnoses whose cleaned string contains any of these substrings are also excluded.
# Case-insensitive.
EXCLUDED_SUBSTRINGS: tuple[str, ...] = (
    "asthma",
    "arterielle",
    "adipos",
)

# ==============================
# NOISE FILTERS
# Applied to diagnosis_unique outputs only. Raw outputs unchanged.
# ==============================

# Diagnoses starting with these lowercase words are sentence fragments, not diagnoses.
_NOISE_PREFIXES = re.compile(
    r"^(bei|mit|nach|unter|im|an|als|durch|für|bekannter?|beginnender?|"
    r"aufgrund|infolge|sowie|und|oder)\b",
    re.IGNORECASE,
)

# Diagnoses containing dosage patterns are medication entries, not diagnoses.
_NOISE_DOSAGE = re.compile(r"\b(mg|ml|mmol|1-0-0|0-0-1|wöchentlich|täglich|monatlich)\b", re.IGNORECASE)


def _is_noise(diagnosis: str) -> bool:
    # starts with a digit
    if diagnosis and diagnosis[0].isdigit():
        return True
    # starts with a lowercase letter (German diagnoses always start with capital)
    if diagnosis and diagnosis[0].islower():
        return True
    # sentence fragment starting with preposition/article
    if _NOISE_PREFIXES.match(diagnosis):
        return True
    # medication dosage entry
    if _NOISE_DOSAGE.search(diagnosis):
        return True
    return False

# ==============================
# REGEX
# ==============================

ICD_AT_END_REGEX = re.compile(
    r"^(?P<diagnosis>.+?)\s+(?P<icd>[A-Z][0-9]{1,2}(?:\.[0-9A-Z]{1,4})?)\s*$"
)

ICD_AT_START_REGEX = re.compile(
    r"^(?P<icd>[A-Z][0-9]{1,2}(?:\.[0-9A-Z]{1,4})?)\s+(?P<diagnosis>.+?)\s*$"
)

# ==============================
# HELPERS
# ==============================

def read_docx_text(path: Path) -> str:
    from docx import Document
    doc = Document(path)
    lines = []
    for p in doc.paragraphs:
        cleaned = " ".join(p.text.split())
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


# Strip leading bullet/formatting characters and collapse whitespace
_PREFIX_JUNK = re.compile(r"^[\s\*\-\–\•\·\(\)\[\]]+")

def clean_diagnosis(text: str) -> str:
    text = _PREFIX_JUNK.sub("", text)
    return " ".join(text.split()).strip()


def parse_diagnosis_icd_line(line: str):
    cleaned = normalize_line(line)

    m = ICD_AT_END_REGEX.match(cleaned)
    if m:
        return m.group("diagnosis").strip(), m.group("icd").strip()

    m = ICD_AT_START_REGEX.match(cleaned)
    if m:
        return m.group("diagnosis").strip(), m.group("icd").strip()

    return None

# ==============================
# MAIN
# ==============================

def main():
    diagnosis_rows    = []
    diagnosis_counter = defaultdict(int)
    icd_counter       = defaultdict(int)
    unique_counter    = defaultdict(int)   # (diagnosis, icd) -> count
    inventory_rows    = []
    errors            = []

    files = sorted(DATASET_DIR.glob("*.docx")) + sorted(DATASET_DIR.glob("*.txt"))
    total = len(files)

    print(f"Nalezeno souboru: {total}")

    jsonl_path = OUTPUT_DIR / "text_export.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as jsonl_f:

        for i, file_path in enumerate(files, 1):
            if i % 100 == 0 or i == 1:
                print(f"  [{i}/{total}] {file_path.name}")

            suffix = file_path.suffix.lower()
            file_diagnoses = 0
            status = "ok"

            try:
                if suffix == ".docx":
                    text = read_docx_text(file_path)
                elif suffix == ".txt":
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                else:
                    continue

                lines = text.split("\n")

                for line_no, line in enumerate(lines):
                    parsed = parse_diagnosis_icd_line(line)
                    if parsed:
                        diagnosis_text, icd_code = parsed
                        diagnosis_rows.append([
                            file_path.name,
                            str(file_path),
                            line_no,
                            line,
                            diagnosis_text,
                            icd_code,
                        ])
                        diagnosis_counter[diagnosis_text.lower()] += 1
                        icd_counter[f"{diagnosis_text} | {icd_code}"] += 1
                        unique_counter[(clean_diagnosis(diagnosis_text), icd_code)] += 1
                        file_diagnoses += 1

                # Write to JSONL
                jsonl_f.write(json.dumps({
                    "file": file_path.name,
                    "text": text,
                }, ensure_ascii=False) + "\n")

            except Exception as e:
                status = f"error: {e}"
                errors.append((file_path.name, str(e)))
                print(f"  [CHYBA] {file_path.name}: {e}")

            inventory_rows.append([file_path.name, str(file_path), suffix, file_diagnoses, status])

    # ==============================
    # EXPORT
    # ==============================

    print("Ukladam vystupy...")

    # files_inventory.csv
    with open(OUTPUT_DIR / "files_inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "path", "suffix", "diagnosis_count", "status"])
        writer.writerows(inventory_rows)

    # diagnosis_candidates_raw.csv
    with open(OUTPUT_DIR / "diagnosis_candidates_raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "path", "line_no", "raw_line", "diagnosis", "icd"])
        writer.writerows(diagnosis_rows)

    # diagnosis_frequency_raw.csv
    with open(OUTPUT_DIR / "diagnosis_frequency_raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["diagnosis", "count"])
        for diag, count in sorted(diagnosis_counter.items(), key=lambda x: -x[1]):
            writer.writerow([diag, count])

    # diagnosis_frequency_by_icd.csv
    with open(OUTPUT_DIR / "diagnosis_frequency_by_icd.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["diagnosis | icd", "count"])
        for key, count in sorted(icd_counter.items(), key=lambda x: -x[1]):
            writer.writerow([key, count])

    # diagnosis_unique.csv  (alphabetical, no count)
    def _is_excluded(diagnosis: str) -> bool:
        d = diagnosis.lower()
        return (
            d in EXCLUDED_DIAGNOSES
            or any(s in d for s in EXCLUDED_SUBSTRINGS)
            or _is_noise(diagnosis)
        )

    unique_sorted = sorted(
        (k for k in unique_counter if not _is_excluded(k[0])),
        key=lambda x: x[0].lower(),
    )
    with open(OUTPUT_DIR / "diagnosis_unique.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["diagnosis", "icd"])
        for diagnosis, icd in unique_sorted:
            writer.writerow([diagnosis, icd])

    # diagnosis_unique_with_count.csv  (alphabetical + count)
    with open(OUTPUT_DIR / "diagnosis_unique_with_count.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["diagnosis", "icd", "count"])
        for diagnosis, icd in unique_sorted:
            writer.writerow([diagnosis, icd, unique_counter[(diagnosis, icd)]])

    # ==============================
    # SUMMARY
    # ==============================

    processed = sum(1 for r in inventory_rows if r[4] == "ok")
    total_diagnoses = len(diagnosis_rows)

    print(f"\nHOTOVO")
    print(f"   Zpracovane soubory        : {processed}/{total}")
    print(f"   Chyby                     : {len(errors)}")
    print(f"   Nalezene diagnozy (radky) : {total_diagnoses}")
    print(f"   Unikatni kombinace        : {len(unique_sorted)}")
    print(f"\nPrvnich 50 radku z diagnosis_unique.csv:")
    for diagnosis, icd in unique_sorted[:50]:
        print(f"   {diagnosis} | {icd}")

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    main()
