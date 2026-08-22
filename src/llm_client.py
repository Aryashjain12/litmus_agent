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


def call_llm(client, model: str, system: str, user: str, max_tokens: int = 500, json_object: bool = False) -> str:
    # Groq's free tier has a low tokens-per-minute cap, and this pipeline
    # fires many sequential calls (one per paper) -- back off and retry
    # rather than letting a single rate-limit response kill a live demo.
    kwargs = {
        # The current Groq lineup (gpt-oss-20b/120b) are reasoning models that
        # spend part of max_tokens on a hidden reasoning trace before the
        # visible answer. "low" keeps that overhead small and predictable --
        # without it, tight token budgets can come back with empty content.
        "reasoning_effort": "low",
    }
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
