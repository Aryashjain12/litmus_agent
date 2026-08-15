"""
Stage 3: Compare claims across all papers and flag genuine contradictions.

This is the core "hard reasoning" step and the track's bonus feature --
give it the full claim set in one call rather than pairwise (pairwise is
O(n^2) calls and mostly wasted on obviously-unrelated pairs; one call with
everything lets Claude use judgment about which pairs are worth comparing).
"""

from __future__ import annotations

import json

from .llm_client import call_llm
from .schemas import CONTRADICTION_SCHEMA

DETECTOR_MODEL = "llama-3.3-70b-versatile"

_SYSTEM = f"""You are comparing findings extracted from multiple research papers
to find genuine contradictions -- cases where two papers make claims that
cannot both be true, not just claims that differ in scope, method, or framing.

Be conservative: only flag a pair if the disagreement is real and specific.
"Paper A studied X and paper B studied Y" is NOT a contradiction. "Paper A
found X improves outcomes, paper B found X has no effect on the same outcome
under comparable conditions" IS a contradiction.

Respond with ONLY a JSON array of objects matching this schema (empty array
if you find no genuine contradictions -- do not force one):

{json.dumps(CONTRADICTION_SCHEMA, indent=2)}

No prose, no markdown fences."""


def detect_contradictions(client, claims: list[dict]) -> list[dict]:
    if len(claims) < 2:
        return []

    claims_summary = "\n\n".join(
        f"[{c['paper_id']}] {c['title']}\n"
        f"  Methodology: {c['methodology']}\n"
        f"  Key finding: {c['key_finding']}"
        for c in claims
    )

    text = call_llm(client, DETECTOR_MODEL, _SYSTEM, claims_summary, max_tokens=2000)
    try:
        contradictions = json.loads(text)
        assert isinstance(contradictions, list)
        return contradictions
    except (json.JSONDecodeError, AssertionError):
        return []
