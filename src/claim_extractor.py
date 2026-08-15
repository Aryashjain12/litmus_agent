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
Respond with ONLY a JSON object matching this schema, no prose, no markdown fences.
Every field must be a plain string -- never a nested object or a list.

{json.dumps(CLAIM_SCHEMA, indent=2)}

Base every field only on what the abstract actually states. If something
isn't in the abstract, say so explicitly (e.g. "Not specified") -- never
invent details."""

_RETRY_SUFFIX = (
    "\n\nYour previous response was invalid -- either malformed JSON or a "
    "field that wasn't a plain string. Return a corrected JSON object where "
    "every field is a plain string."
)


def _valid(extracted: dict) -> bool:
    return all(isinstance(extracted.get(field), str) for field in CLAIM_SCHEMA["required"])


def extract_claims(client, paper: dict) -> dict | None:
    """Return a claim record for one paper, or None if extraction fails.

    Retries once on a malformed response -- a single formatting slip from
    the smaller/faster model shouldn't cost the pipeline a whole paper.
    """
    content = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"

    for attempt in range(2):
        prompt = content if attempt == 0 else content + _RETRY_SUFFIX
        text = call_llm(client, EXTRACTOR_MODEL, _SYSTEM, prompt, max_tokens=500, json_object=True)
        try:
            extracted = json.loads(text)
        except json.JSONDecodeError:
            continue
        if _valid(extracted):
            return make_claim_record(paper, extracted)
    return None
