"""
Stage 4: Synthesize the final report -- a short summary paragraph plus a
literature matrix. The bibliography is built directly from paper metadata
(no need to ask Claude for citation formatting -- that's a good way to get
subtly wrong citations).
"""

from __future__ import annotations

from .llm_client import call_llm

SYNTHESIZER_MODEL = "openai/gpt-oss-120b"

_SYSTEM = """You are writing the closing summary of a literature review agent's
report. Given the research question, the extracted claims, and any flagged
contradictions, write a concise (150-250 word) synthesis paragraph: what the
literature broadly says, and -- importantly -- where it disagrees and why
that matters for someone trying to answer the research question. Plain text,
no markdown headers."""


def synthesize_summary(client, research_question: str, claims: list[dict], contradictions: list[dict]) -> str:
    claims_text = "\n".join(f"- [{c['paper_id']}] {c['key_finding']}" for c in claims)
    contradictions_text = (
        "\n".join(
            f"- [{c.get('severity', 'moderate')}] {c['topic']}: {c['paper_a_id']} vs {c['paper_b_id']} -- {c['explanation']}"
            for c in contradictions
        )
        or "None found."
    )

    content = (
        f"Research question: {research_question}\n\n"
        f"Findings:\n{claims_text}\n\n"
        f"Flagged contradictions:\n{contradictions_text}"
    )

    return call_llm(client, SYNTHESIZER_MODEL, _SYSTEM, content, max_tokens=500)


def build_bibliography(claims: list[dict]) -> list[dict]:
    """Plain metadata list -- no Claude call needed."""
    return [
        {
            "id": c["paper_id"],
            "title": c["title"],
            "year": c.get("year"),
            "url": c.get("url"),
            "citation": c.get("citation"),
        }
        for c in claims
    ]
