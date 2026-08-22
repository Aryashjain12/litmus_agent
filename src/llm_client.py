"""
Shared LLM call helper -- wraps the Groq client so all four pipeline
stages call through one place. Groq's API is OpenAI-compatible
(chat.completions.create), unlike Anthropic's messages.create, so this
keeps that difference contained to one spot instead of four.
"""

from __future__ import annotations

import time

from groq import RateLimitError

MAX_RETRIES = 4

# GPT-OSS likes typographic Unicode (non-breaking hyphens, curly quotes,
# en/em dashes) even when asked for plain text. Harmless in prose, but fatal
# for arXiv search terms: a query with U+2011 instead of "-" matches almost
# nothing, since real paper text uses the ASCII hyphen.
_TYPOGRAPHIC_TO_ASCII = str.maketrans({
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...",
})


def _normalize_text(text: str) -> str:
    return text.translate(_TYPOGRAPHIC_TO_ASCII)


def call_llm(
    client,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 500,
    json_object: bool = False,
    reasoning_effort: str = "low",
) -> str:
    # Groq's free tier has a low tokens-per-minute cap, and this pipeline
    # fires many sequential calls (one per paper) -- back off and retry
    # rather than letting a single rate-limit response kill a live demo.
    #
    # reasoning_effort controls how much hidden "thinking" the model does
    # before answering. "low" is right for cheap, repetitive calls (one per
    # paper extraction) -- but the contradiction-detection stage genuinely
    # needs to cross-check numeric claims across every paper at once, and
    # "low" effort there was causing it to under-analyze and default to
    # "no contradictions" rather than doing that comparison work. Callers
    # that need real cross-document reasoning should pass "medium"/"high".
    kwargs = {"reasoning_effort": reasoning_effort}
    if json_object:
        # Forces syntactically valid JSON -- only usable when the expected
        # output is a JSON *object*, not an array (the API rejects the latter).
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **kwargs,
            )
            break
        except RateLimitError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
    text = _normalize_text(resp.choices[0].message.content.strip())
    # Models sometimes wrap JSON in markdown fences despite being told not to.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return text
