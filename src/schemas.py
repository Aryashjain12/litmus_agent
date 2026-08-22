"""
Structured-output schemas shared by the pipeline stages.

These are plain dicts (not pydantic) on purpose -- for a hackathon build you
want to move fast and print/debug raw JSON without fighting a validation
layer. Tighten this later if you have time.
"""

# Passed to Claude as a JSON schema description in the extraction prompt.
CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "methodology": {
            "type": "string",
            "description": "One sentence: what approach/method the paper used.",
        },
        "dataset_or_sample": {
            "type": "string",
            "description": "What data, benchmark, or sample size was used. 'Not specified' if unclear.",
        },
        "key_finding": {
            "type": "string",
            "description": "The paper's main quantitative or qualitative result, one to two sentences.",
        },
        "limitations": {
            "type": "string",
            "description": "Any limitation the authors note, or 'Not stated' if none found.",
        },
    },
    "required": ["methodology", "dataset_or_sample", "key_finding", "limitations"],
}

def _format_citation(paper: dict) -> str:
    """'Lastname et al., Year' -- a real citable reference, not just a link."""
    authors = paper.get("authors") or []
    year = paper.get("year") or "n.d."
    if not authors or not authors[0]:
        return f"Unknown Author, {year}"
    last_name = authors[0].strip().split()[-1]
    return f"{last_name}, {year}" if len(authors) == 1 else f"{last_name} et al., {year}"


# One extracted claim, with paper metadata attached so downstream stages
# don't need to re-join against the paper list.
def make_claim_record(paper: dict, extracted: dict) -> dict:
    return {
        "paper_id": paper["id"],
        "title": paper["title"],
        "url": paper.get("url"),
        "year": paper.get("year"),
        "citation": _format_citation(paper),
        "citation_count": paper.get("citation_count"),
        **extracted,
    }


# A single flagged contradiction between two papers' claims.
CONTRADICTION_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "description": "Short label for what the papers disagree about."},
        "severity": {
            "type": "string",
            "enum": ["strong", "moderate"],
            "description": (
                "'strong' if the two claims directly negate each other under comparable "
                "conditions (same task/metric/setting). 'moderate' if they conflict in "
                "overall direction but differ somewhat in scope, domain, or setup."
            ),
        },
        "paper_a_id": {"type": "string"},
        "paper_a_claim": {"type": "string", "description": "The specific claim from paper A, in your own words."},
        "paper_b_id": {"type": "string"},
        "paper_b_claim": {"type": "string", "description": "The specific claim from paper B, in your own words."},
        "explanation": {"type": "string", "description": "Why these two claims genuinely conflict, not just differ in framing."},
    },
    "required": ["topic", "severity", "paper_a_id", "paper_a_claim", "paper_b_id", "paper_b_claim", "explanation"],
}
