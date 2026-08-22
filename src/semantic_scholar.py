"""
Semantic Scholar search -- free, no key required for the public search
endpoint (low request volume is fine for a demo; add an API key in
.env as S2_API_KEY if you hit rate limits and want higher throughput).

Docs: https://api.semanticscholar.org/api-docs/graph
"""

from __future__ import annotations

import os
import time

import requests

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,year,authors,citationCount,externalIds,url"
MAX_RETRIES = 3


def search_semantic_scholar(query: str, limit: int = 8) -> list[dict]:
    headers = {}
    api_key = os.getenv("S2_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    params = {"query": query, "limit": limit, "fields": FIELDS}

    # The unauthenticated free tier has a low, easily-exhausted rate limit --
    # a run that fires several queries in a row can trip it mid-pipeline.
    # Back off and retry rather than silently losing this whole source.
    for attempt in range(MAX_RETRIES):
        resp = requests.get(S2_API, params=params, headers=headers, timeout=15)
        if resp.status_code == 429 and attempt < MAX_RETRIES - 1:
            time.sleep(2 * (attempt + 1))  # 2s, 4s
            continue
        resp.raise_for_status()
        break
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        if not item.get("abstract"):
            continue  # skip papers we can't extract claims from
        paper_id = item.get("paperId", "")
        authors = [a.get("name", "") for a in item.get("authors", [])]
        papers.append(
            {
                "id": f"s2:{paper_id}",
                "source": "semantic_scholar",
                "title": item.get("title", ""),
                "abstract": item.get("abstract", ""),
                "authors": authors,
                "year": item.get("year"),
                "citation_count": item.get("citationCount"),
                "url": item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
            }
        )
    return papers
