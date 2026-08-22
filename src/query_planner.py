"""
Stage 1: Plan search queries.

Takes the user's raw research question and asks Claude to decompose it into
2-4 targeted search-engine queries. This is what makes the agent read as
"planning" rather than "forwarding the user's text to a search box".
"""

from __future__ import annotations

import json

from .llm_client import call_llm

PLANNER_MODEL = "openai/gpt-oss-120b"

_SYSTEM = """You are the planning stage of a literature-review research agent.
Given a research question, produce 2-4 short search queries (3-8 words each)
that together would surface the most relevant academic papers, including
queries likely to surface papers that DISAGREE with each other -- this agent's
job is specifically to find contested findings, not just a consensus view.

Respond with ONLY a JSON array of strings. No prose, no markdown fences."""


def plan_queries(client, research_question: str, refine_hint: str | None = None) -> list[str]:
    """Return a list of search query strings.

    If refine_hint is given (e.g. "previous search returned too few papers
    with usable abstracts"), the prompt asks Claude to broaden or rephrase.
    """
    user_content = f"Research question: {research_question}"
    if refine_hint:
        user_content += f"\n\nPrevious search was insufficient because: {refine_hint}\nProduce different or broader queries this time."

    text = call_llm(client, PLANNER_MODEL, _SYSTEM, user_content, max_tokens=450)
    try:
        queries = json.loads(text)
        assert isinstance(queries, list) and all(isinstance(q, str) for q in queries)
        return queries
    except (json.JSONDecodeError, AssertionError):
        # Fallback: treat the raw question as a single query rather than
        # crashing the pipeline over a formatting slip.
        return [research_question]
