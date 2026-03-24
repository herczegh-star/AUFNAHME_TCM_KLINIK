"""
document_service.py
-------------------
Inserts composed text blocks into the "Derzeitige Beschwerden (somatisch)"
section of an existing Aufnahme-Schablone .docx file.

Strategy:
- Find the paragraph starting with "Derzeitige Beschwerden"
- Find the paragraph starting with "Vormedikation"
- Delete all paragraphs between them
- Insert new blocks before "Vormedikation"
- Save in place

Uses direct XML manipulation via python-docx / lxml because python-docx
has no first-class "insert paragraph at index" API.

Raises ValueError if either section marker is not found.
Raises on IO errors — caller handles user feedback.
"""

from __future__ import annotations

from pathlib import Path


def insert_blocks_into_section(path: Path, blocks: list[str]) -> None:
    from docx import Document
    from docx.oxml import OxmlElement

    doc  = Document(path)
    body = doc.element.body

    start_p = None
    end_p   = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if start_p is None and text.startswith("Derzeitige Beschwerden"):
            start_p = para._p
        elif start_p is not None and text.startswith("Vormedikation"):
            end_p = para._p
            break

    if start_p is None:
        raise ValueError("Abschnitt 'Derzeitige Beschwerden' nicht gefunden.")
    if end_p is None:
        raise ValueError("Abschnitt 'Vormedikation' nicht gefunden.")

    # Remove all paragraphs between start and end
    current = start_p.getnext()
    while current is not None and current is not end_p:
        nxt = current.getnext()
        body.remove(current)
        current = nxt

    # Insert new block paragraphs before end_p, preserving order
    for block in blocks:
        new_p = OxmlElement("w:p")
        new_r = OxmlElement("w:r")
        new_t = OxmlElement("w:t")
        new_t.text = block
        new_r.append(new_t)
        new_p.append(new_r)
        end_p.addprevious(new_p)

    doc.save(path)
