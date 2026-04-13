"""
llm_client.py
-------------
Minimal OpenAI-compatible LLM client for the Pilot-Composer draft pipeline.

Provides one public function:

    call_llm(system, user, temperature=0.2) -> str

Used by services/pilot_draft_service.py for:
  Stage 2 — generate_refined   (grammar/flow cleanup)
  Stage 3 — generate_final     (Verdichtungsstil pass)
  Assembly — generate_connected (multi-block linguistic connection)

This module is intentionally minimal — no streaming, no async, no retry.
All threading is handled by the callers in pilot_draft_service.py.
"""

from __future__ import annotations

import os
from pathlib import Path

# Load .env from project root — safe: no-op if python-dotenv is not installed
# or if the file does not exist.  Must happen before os.environ is read.
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — rely on env vars being set externally

_MODEL = "gpt-4o-mini"
_MAX_TOKENS = 2048


def call_llm(system: str, user: str, temperature: float = 0.2) -> str:
    """
    Send a system + user message to gpt-4o-mini and return the response text.

    Parameters
    ----------
    system      : system-role prompt text
    user        : user-role message text
    temperature : sampling temperature (default 0.2 for clinical text)

    Returns
    -------
    str — stripped response content from the model

    Raises
    ------
    ValueError      if OPENAI_API_KEY is missing or blank
    RuntimeError    if the API response contains no usable text
    openai.APIError and subclasses propagate to the caller as-is
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set or empty. "
            "Add it to the project .env file or set it as an environment variable."
        )

    from openai import OpenAI  # imported here so missing SDK raises ImportError cleanly

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )

    text = response.choices[0].message.content
    if not text or not text.strip():
        raise RuntimeError(
            f"call_llm: model returned an empty response "
            f"(model={_MODEL!r}, finish_reason={response.choices[0].finish_reason!r})."
        )

    return text.strip()
