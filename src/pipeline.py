"""
Orchestrates the full agent: plan -> search -> extract -> evidence check
(retry once if thin) -> compare -> synthesize.

Implemented as a generator that yields log dicts as it goes, so the web
layer can stream progress to the frontend -- this is what makes the demo
visibly "agentic" instead of a black-box spinner.

Usage:
    for event in run_pipeline(client, "does chain-of-thought prompting help reasoning"):
        if event["type"] == "done":
            final_report = event["report"]
        else:
            print(event["message"])
"""

from __future__ import annotations

from groq import APIError, RateLimitError

from .arxiv_search import search_arxiv
from .semantic_scholar import search_semantic_scholar
from .query_planner import plan_queries
from .claim_extractor import extract_claims
from .contradiction_detector import detect_contradictions
from .synthesizer import build_bibliography, synthesize_summary

MIN_USABLE_PAPERS = 5  # evidence-check threshold; tune after a test run
MAX_REFINE_ATTEMPTS = 1  # bounded so a live demo can't loop forever
MAX_PAPERS = 15  # keeps per-run LLM calls (and free-tier rate limits) in check


def _log(message: str) -> dict:
    return {"type": "log", "message": message}


def _search_all(queries: list[str]) -> list[dict]:
    papers, seen_titles = [], set()
    for q in queries:
        for fetch in (search_arxiv, search_semantic_scholar):
            try:
                for p in fetch(q, 8):
                    key = p["title"].strip().lower()
                    if key and key not in seen_titles and p.get("abstract"):
                        seen_titles.add(key)
                        papers.append(p)
            except Exception:
                # A single source hiccuping should not kill the pipeline
                # mid-demo -- keep going with whatever the other source found.
                continue
    return papers


def run_pipeline(client, research_question: str):
    """Public entry point -- wraps _run_pipeline so an API hiccup ends the
    stream with a readable error event instead of a raw connection drop."""
    try:
        yield from _run_pipeline(client, research_question)
    except RateLimitError:
        yield {
            "type": "done",
            "report": None,
            "error": "Hit the LLM provider's rate limit. Wait a minute and try again.",
        }
    except APIError as exc:
        yield {"type": "done", "report": None, "error": f"LLM provider error: {exc}"}
    except Exception:
        yield {"type": "done", "report": None, "error": "Unexpected error -- check server logs."}


def _run_pipeline(client, research_question: str):
    refine_hint = None
    papers: list[dict] = []

    for attempt in range(MAX_REFINE_ATTEMPTS + 1):
        yield _log("Planning search queries..." if attempt == 0 else "Refining search queries...")
        queries = plan_queries(client, research_question, refine_hint)
        yield _log(f"Queries: {', '.join(queries)}")

        yield _log("Searching arXiv and Semantic Scholar...")
        papers = _search_all(queries)[:MAX_PAPERS]
        yield _log(f"Found {len(papers)} papers with usable abstracts")

        if len(papers) >= MIN_USABLE_PAPERS or attempt == MAX_REFINE_ATTEMPTS:
            break
        refine_hint = f"only {len(papers)} papers with usable abstracts were found"

    claims = []
    for i, paper in enumerate(papers, 1):
        yield _log(f"Extracting claims ({i}/{len(papers)}): {paper['title'][:60]}...")
        record = extract_claims(client, paper)
        if record:
            claims.append(record)

    if not claims:
        yield {"type": "done", "report": None, "error": "No papers yielded usable claims."}
        return

    # Most-cited first -- a cheap, honest proxy for relevance in the
    # rendered matrix/bibliography (arXiv papers without a citation count
    # sort after everything that has one).
    claims.sort(key=lambda c: c.get("citation_count") or 0, reverse=True)

    yield _log(f"Comparing {len(claims)} papers' claims for contradictions...")
    contradictions = detect_contradictions(client, claims)
    yield _log(f"Flagged {len(contradictions)} contradiction(s)")

    yield _log("Synthesizing final report...")
    summary = synthesize_summary(client, research_question, claims, contradictions)
    bibliography = build_bibliography(claims)

    report = {
        "research_question": research_question,
        "summary": summary,
        "claims": claims,
        "contradictions": contradictions,
        "bibliography": bibliography,
    }
    yield {"type": "done", "report": report, "error": None}
