"""
arXiv search -- free, no API key, no rate-limit headaches. Good primary
source for a live demo since it will not fail on stage.

Docs: https://info.arxiv.org/help/api/user-manual.html
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

ARXIV_API = "http://export.arxiv.org/api/query"

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def search_arxiv(query: str, max_results: int = 8) -> list[dict]:
    """Search arXiv and return a list of paper dicts.

    Each paper dict: id, title, abstract, authors, year, url.
    """
    # AND each word together instead of a loose multi-term match -- arXiv's
    # default parsing lets a single common word (e.g. "chain") pull in
    # completely unrelated papers that happen to contain it once.
    terms = " AND ".join(f"all:{word}" for word in query.split())
    params = {
        "search_query": terms,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API, params=params, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    papers = []
    for entry in root.findall("atom:entry", _NS):
        arxiv_id = entry.findtext("atom:id", default="", namespaces=_NS).rsplit("/", 1)[-1]
        title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip().replace("\n", " ")
        abstract = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip().replace("\n", " ")
        published = entry.findtext("atom:published", default="", namespaces=_NS) or ""
        year = published[:4] if published else None
        authors = [
            a.findtext("atom:name", default="", namespaces=_NS)
            for a in entry.findall("atom:author", _NS)
        ]
        papers.append(
            {
                "id": f"arxiv:{arxiv_id}",
                "source": "arxiv",
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "year": year,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
            }
        )
    return papers
