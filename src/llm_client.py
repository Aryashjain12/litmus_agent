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


def call_llm(client, model: str, system: str, user: str, max_tokens: int = 500, json_object: bool = False) -> str:
    # Groq's free tier has a low tokens-per-minute cap, and this pipeline
    # fires many sequential calls (one per paper) -- back off and retry
    # rather than letting a single rate-limit response kill a live demo.
    kwargs = {}
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
    text = resp.choices[0].message.content.strip()
    # Models sometimes wrap JSON in markdown fences despite being told not to.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return text
