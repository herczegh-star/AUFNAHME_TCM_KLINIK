"""
document_service.py
-------------------
Writes composed text blocks into an existing Aufnahme-Schablone .docx file.
"""

from __future__ import annotations

from pathlib import Path


def append_blocks_to_docx(path: Path, blocks: list[str]) -> None:
    """
    Appends each block as a new paragraph to an existing .docx file.
    An empty paragraph is added between blocks.
    Raises on any IO or format error — caller handles user feedback.
    """
    from docx import Document
    doc = Document(path)
    for block in blocks:
        doc.add_paragraph(block)
        doc.add_paragraph("")
    doc.save(path)
