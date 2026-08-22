"""
Follow-up Q&A on a completed report.

The pipeline already extracted structured claims from every paper -- this
lets a user interrogate that extracted evidence directly ("which paper had
the largest sample size?", "summarize the medical papers only") without
re-running search or extraction. One call, grounded strictly in the report
already on hand -- if the answer isn't in there, it says so rather than
reaching for outside knowledge.
"""

from __future__ import annotations

from .llm_client import call_llm

QA_MODEL = "openai/gpt-oss-120b"

_SYSTEM = """You are answering a follow-up question about a literature review
that has already been completed. You are given the research question, the
synthesized summary, every paper's extracted claim (methodology, dataset,
key finding, limitations, citation), and any flagged contradictions.

Answer using ONLY this information -- never bring in outside knowledge about
the topic. If the answer genuinely is not contained in what's given, say so
plainly ("The analyzed papers don't report that") instead of guessing.

When you reference a paper, use its citation (e.g. "Smith et al., 2024") so
the answer stays traceable to a source. Keep the answer concise -- a few
sentences unless the question asks for a list."""


def _format_context(report: dict) -> str:
    claims_text = "\n\n".join(
        f"[{c.get('citation', c.get('paper_id', 'Unknown'))}] {c['title']}\n"
        f"  Methodology: {c.get('methodology', 'Not specified')}\n"
        f"  Dataset/sample: {c.get('dataset_or_sample', 'Not specified')}\n"
        f"  Key finding: {c.get('key_finding', 'Not specified')}\n"
        f"  Limitations: {c.get('limitations', 'Not stated')}"
        for c in report.get("claims", [])
    )
    contradictions_text = (
        "\n".join(
            f"- [{c.get('severity', 'moderate')}] {c['topic']}: "
            f"{c['paper_a_id']} says \"{c['paper_a_claim']}\" vs "
            f"{c['paper_b_id']} says \"{c['paper_b_claim']}\""
            for c in report.get("contradictions", [])
        )
        or "None flagged."
    )
    return (
        f"Research question: {report.get('research_question', '')}\n\n"
        f"Summary: {report.get('summary', '')}\n\n"
        f"Papers and extracted claims:\n{claims_text}\n\n"
        f"Flagged contradictions:\n{contradictions_text}"
    )


def answer_followup(client, report: dict, question: str) -> str:
    context = _format_context(report)
    user_content = f"{context}\n\n---\n\nFollow-up question: {question}"
    return call_llm(client, QA_MODEL, _SYSTEM, user_content, max_tokens=400)
