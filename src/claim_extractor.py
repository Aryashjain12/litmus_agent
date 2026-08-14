"""
Stage 2: Extract structured claims from one paper's abstract.

Uses a cheaper/faster model since this runs once per paper (potentially
10-15 calls per research question) -- keep it fast and keep cost down.
"""

from __future__ import annotations

import json

from .llm_client import call_llm
from .schemas import CLAIM_SCHEMA, make_claim_record

EXTRACTOR_MODEL = "llama-3.1-8b-instant"

_SYSTEM = f"""Extract structured information from this paper's title and abstract.
Respond with ONLY a JSON object matching this schema, no prose, no markdown fences:

{json.dumps(CLAIM_SCHEMA, indent=2)}

Base every field only on what the abstract actually states. If something
isn't in the abstract, say so explicitly (e.g. "Not specified") -- never
invent details."""


def extract_claims(client, paper: dict) -> dict | None:
    """Return a claim record for one paper, or None if extraction fails."""
    content = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"

    text = call_llm(client, EXTRACTOR_MODEL, _SYSTEM, content, max_tokens=500, json_object=True)
    try:
        extracted = json.loads(text)
        if not all(field in extracted for field in CLAIM_SCHEMA["required"]):
            return None  # smaller models occasionally drop a required field
        return make_claim_record(paper, extracted)
    except json.JSONDecodeError:
        return None
