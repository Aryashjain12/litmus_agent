# Contradiction-aware literature review agent

Built for **Ascendant Agents** (D'Code NSUT), Track 4: AI Academic Research Assistant.

## Overview

Literature review is slow because it's not really a search problem, it's a
synthesis problem: you have to read a pile of papers and notice where they
quietly disagree with each other. This agent automates that specific step.

Give it a research question and it plans a search, retrieves papers from
arXiv and Semantic Scholar, extracts a structured claim from each one, and
then compares those claims to flag genuine contradictions -- not just
related papers, but papers whose findings actually conflict. It closes with
a synthesized summary, a literature matrix, and a sourced bibliography.

If the first search doesn't turn up enough usable papers, the agent
re-plans its query and searches again before giving up -- it doesn't just
run one fixed pipeline and report whatever it got.

## Tech stack

- **Groq** (Llama 3.3 70B / Llama 3.1 8B) -- query planning, claim extraction, contradiction detection, synthesis
- **arXiv API** -- free, no auth, primary paper source
- **Semantic Scholar API** -- free, secondary source with citation counts
- **FastAPI** -- backend, streams agent progress over Server-Sent Events
- Plain HTML/CSS/JS frontend -- no build step, fast to iterate on during the hackathon

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY (free at console.groq.com/keys)
uvicorn app:app --reload --port 8000
```

Open `http://localhost:8000`, type a research question, and watch the agent's
steps stream in live before the report renders.

## Features

- Multi-query search planning (not a single forwarded search string)
- Dual-source retrieval (arXiv + Semantic Scholar) with deduplication
- Structured claim extraction per paper (methodology, dataset, finding, limitations)
- Cross-paper contradiction detection with cited evidence from both sides
- Evidence-sufficiency check with a bounded re-search loop
- Synthesized summary + literature matrix + bibliography
- Live agent trace in the UI (no black-box spinner)

## Technical workflow

1. **Plan search queries** -- the LLM decomposes the research question into
   2-4 targeted queries, deliberately including queries likely to surface
   *disagreeing* papers, not just a consensus view.
2. **Search & retrieve** -- each query hits arXiv (terms ANDed together so a
   single common word can't pull in unrelated papers) and Semantic Scholar;
   results are merged, deduplicated by title, and capped at `MAX_PAPERS`.
3. **Extract claims** -- one call per paper returns a fixed JSON record:
   methodology, dataset/sample, key finding, limitations.
4. **Evidence check** -- if fewer than `MIN_USABLE_PAPERS` papers yielded
   usable claims, the agent re-plans and searches again (bounded to one
   retry).
5. **Detect contradictions** -- one call receives every extracted claim
   together and flags pairs that genuinely conflict, with the specific
   claims and an explanation for each.
6. **Synthesize** -- a closing summary paragraph plus a literature matrix
   and bibliography built from the paper metadata already on hand.

## Project structure

```
app.py                        FastAPI server + SSE streaming endpoint
src/
  arxiv_search.py             arXiv API wrapper
  semantic_scholar.py         Semantic Scholar API wrapper
  query_planner.py            Stage 1: search query planning
  claim_extractor.py          Stage 2: per-paper structured extraction
  contradiction_detector.py   Stage 3: cross-paper contradiction detection
  synthesizer.py              Stage 4: summary + bibliography
  pipeline.py                 Orchestrates all stages, yields progress events
  schemas.py                  Shared JSON schemas for structured output
static/index.html             Demo frontend
```

## Team

_Add your team members here._
