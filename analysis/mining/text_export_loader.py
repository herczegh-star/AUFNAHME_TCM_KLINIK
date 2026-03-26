"""
text_export_loader.py
---------------------
Load and validate text_export.jsonl into TextDocument objects.

Each line must be valid JSON with keys "file" and "text".
Malformed lines are skipped with a warning — not fatal.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from analysis.mining.models import TextDocument

logger = logging.getLogger(__name__)


class TextExportLoader:
    """
    Loads text_export.jsonl line by line.

    Usage:
        loader = TextExportLoader("path/to/text_export.jsonl")
        docs   = loader.load()
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> list[TextDocument]:
        """
        Read all valid lines from the JSONL file.

        Returns a list of TextDocument objects.
        Raises FileNotFoundError if the file does not exist.
        """
        if not self._path.exists():
            raise FileNotFoundError(f"text_export not found: {self._path}")

        docs: list[TextDocument] = []
        skipped = 0

        with self._path.open(encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                doc = self._parse_line(raw, lineno)
                if doc is not None:
                    docs.append(doc)
                else:
                    skipped += 1

        logger.info(
            "TextExportLoader: loaded %d docs, skipped %d lines from %s",
            len(docs), skipped, self._path.name,
        )
        return docs

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _parse_line(self, raw: str, lineno: int) -> TextDocument | None:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Line %d: JSON decode error — %s", lineno, exc)
            return None

        if not isinstance(obj, dict):
            logger.warning("Line %d: expected dict, got %s", lineno, type(obj).__name__)
            return None

        file_val = obj.get("file", "")
        text_val = obj.get("text", "")

        if not isinstance(file_val, str) or not file_val.strip():
            logger.warning("Line %d: missing or empty 'file' field", lineno)
            return None

        if not isinstance(text_val, str):
            logger.warning("Line %d: 'text' field is not a string", lineno)
            return None

        return TextDocument(file=file_val.strip(), text=text_val)
