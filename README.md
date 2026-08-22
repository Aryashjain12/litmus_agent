# 🧪 Litmus

A contradiction-aware literature review agent. Built for **Ascendant Agents**
(D'Code NSUT), Track 4: AI Academic Research Assistant.

> Give it a research question. It reads real papers, tells you what the
> field agrees on, and — the hard part — tells you exactly where it disagrees.

**Live demo:** [litmus-7dab.onrender.com](https://litmus-7dab.onrender.com/)
_(hosted on Render's free tier — sleeps after 15 min idle, first request after that takes ~30-50s to wake up)_

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

- **Groq** (GPT-OSS 120B / 20B) -- query planning, claim extraction, contradiction detection, synthesis, follow-up Q&A
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

**Two core capabilities:**

1. **Cross-paper contradiction detection** -- not related-paper matching, genuine
   conflict detection. Every flagged contradiction is rated for severity
   (`strong`: claims directly negate each other under comparable conditions,
   vs `moderate`: they conflict in direction but the setup differs enough
   that context could partly explain it) so a reader can tell a hard conflict
   from a nuanced one at a glance.
2. **Follow-up Q&A on the completed review** -- ask a question grounded
   strictly in the claims Litmus already extracted ("which paper had the
   largest sample size?"), with no re-search and no outside-knowledge
   answers. If the analyzed papers don't say, it says so instead of guessing.

**Supporting the two above:**

- Multi-query search planning (not a single forwarded search string)
- Dual-source retrieval (arXiv + Semantic Scholar) with deduplication
- Structured claim extraction per paper (methodology, dataset, finding, limitations, citation)
- Evidence-sufficiency check with a bounded re-search loop
- Citation-aware ordering -- most-cited papers surface first in the matrix/bibliography
- Synthesized summary + literature matrix + bibliography
- Downloadable report (Markdown) and one-click reset for a new query
- Live agent trace in the UI (no black-box spinner)
- Graceful failure -- rate limits, provider errors, and thin search results all
  surface as a readable message in the UI instead of a dead connection
- `/health` endpoint for deployment platform health checks

## Known limitations (by design, not oversight)

- **Abstracts only, not full PDFs.** arXiv and Semantic Scholar's APIs expose
  abstracts without scraping paywalled full text -- a deliberate scope
  trade-off for a hackathon timeline. Going to full-text is the natural next
  step (see Roadmap).
- **Deduplication is title-based.** A preprint and its camera-ready version
  with a slightly reworded title could show up as two entries. A stronger
  version would dedupe by arXiv ID / DOI overlap across sources.
- **Extraction runs sequentially, one LLM call per paper.** At 20 papers this
  pushed past 2 minutes end-to-end, which is why the cap is 17. Parallelizing
  those calls (async) is the obvious next win for both speed and paper count.

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
   together and flags pairs that genuinely conflict, each rated `strong` or
   `moderate`, with the specific claims and an explanation for each.
6. **Synthesize** -- a closing summary paragraph plus a literature matrix
   and bibliography built from the paper metadata already on hand.
7. **Ask follow-ups** -- once the report is done, the same extracted claims
   answer follow-up questions directly (`src/qa.py`) -- no re-search, and it
   says so explicitly when an answer isn't in the analyzed papers.

## Project structure

```
app.py                        FastAPI server + SSE streaming endpoint
src/
  arxiv_search.py             arXiv API wrapper
  semantic_scholar.py         Semantic Scholar API wrapper
  llm_client.py                Shared Groq call helper (retry/backoff, JSON mode)
  query_planner.py            Stage 1: search query planning
  claim_extractor.py          Stage 2: per-paper structured extraction
  contradiction_detector.py   Stage 3: cross-paper contradiction detection, severity-rated
  synthesizer.py              Stage 4: summary + bibliography
  qa.py                       Follow-up Q&A grounded in the completed report
  pipeline.py                 Orchestrates all stages, yields progress events
  schemas.py                  Shared JSON schemas for structured output
static/index.html             Frontend (no build step)
Dockerfile, .dockerignore     Container build
Procfile, render.yaml         Deployment configs (Railway / Render)
```

## Deployment

The app is a single container: FastAPI serves both the API and the static
frontend, so there's nothing to deploy separately.

**Render** (free tier, easiest):
1. Push this repo to GitHub.
2. New → Blueprint on [render.com](https://render.com), point it at the repo
   (it reads `render.yaml` automatically).
3. Add `GROQ_API_KEY` in the dashboard's environment variables.

**Railway**: New Project → Deploy from GitHub repo. Railway auto-detects the
`Procfile`. Add `GROQ_API_KEY` under Variables.

**Any Docker host** (Fly.io, a VPS, etc.):
```bash
docker build -t litmus .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key litmus
```

All three bind to `$PORT` and expose `/health` for the platform's health check.

## Screenshots

See the live demo above for the real thing -- the live agent trace (search
planning, per-paper extraction streaming in) and the final report (severity-
rated contradictions, literature matrix, follow-up Q&A) are best seen running
rather than as static images. Static screenshots are included in the
submission PDF.

## Team

**TechTitan**
- Aryash Jain
- Dhruv Choudhary
- Ashutosh Tomar
