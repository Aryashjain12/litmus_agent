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

DETECTOR_MODEL = "openai/gpt-oss-120b"

_SYSTEM = f"""You are comparing findings extracted from multiple research papers
to find genuine contradictions -- cases where two papers make claims that
cannot both be true, not just claims that differ in scope, method, or framing.

Be conservative: only flag a pair if the disagreement is real and specific.
"Paper A studied X and paper B studied Y" is NOT a contradiction. "Paper A
found X improves outcomes, paper B found X has no effect on the same outcome
under comparable conditions" IS a contradiction.

Rate each one's severity: 'strong' only when the two claims directly negate
each other under comparable conditions (same task, metric, and setting) --
'moderate' when they still conflict in overall direction but the setup
differs enough that context could partly explain it. Do not default every
flag to 'strong' -- most real disagreements in a literature are moderate.

Respond with ONLY a JSON array of objects matching this schema (empty array
if you find no genuine contradictions -- do not force one):

{json.dumps(CONTRADICTION_SCHEMA, indent=2)}

No prose, no markdown fences."""

_REQUIRED_FIELDS = CONTRADICTION_SCHEMA["required"]


def detect_contradictions(client, claims: list[dict]) -> list[dict]:
    if len(claims) < 2:
        return []

    claims_summary = "\n\n".join(
        f"[{c['paper_id']}] {c['title']}\n"
        f"  Methodology: {c['methodology']}\n"
        f"  Dataset/sample: {c.get('dataset_or_sample', 'Not specified')}\n"
        f"  Key finding: {c['key_finding']}"
        for c in claims
    )

    # This is the one stage that genuinely needs real reasoning -- cross-
    # checking numeric claims across every paper, not just pattern matching.
    # Measured empirically: "low" under-analyzes and defaults to empty;
    # "high" either burns the whole token budget on hidden reasoning before
    # writing any answer (empty output, silently parsed as "no
    # contradictions") or reasons its way to over-caution even with room to
    # spare. "medium" is the one that actually finds real contradictions.
    text = call_llm(
        client, DETECTOR_MODEL, _SYSTEM, claims_summary,
        max_tokens=4000, reasoning_effort="medium",
    )
    try:
        contradictions = json.loads(text)
        assert isinstance(contradictions, list)
    except (json.JSONDecodeError, AssertionError):
        return []

    cleaned = []
    for c in contradictions:
        if not isinstance(c, dict) or not all(field in c for field in _REQUIRED_FIELDS):
            continue
        if c.get("severity") not in ("strong", "moderate"):
            c["severity"] = "moderate"  # model occasionally skips the enum constraint
        cleaned.append(c)
    return cleaned
