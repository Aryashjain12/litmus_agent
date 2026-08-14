"""
Minimal web layer. One streaming endpoint (Server-Sent Events) so the
frontend can show the agent's steps live -- that live trace is worth more
in a mentor demo than any amount of UI polish.

Run:
    uvicorn app:app --reload --port 8000
Then open http://localhost:8000
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq

from src.pipeline import run_pipeline

load_dotenv()

app = FastAPI(title="Contradiction-aware literature review agent")
client = Groq(api_key=os.environ["GROQ_API_KEY"])


@app.get("/research/stream")
def research_stream(question: str = Query(..., min_length=5)):
    def event_source():
        for event in run_pipeline(client, question):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


# Serve the demo frontend last so it doesn't shadow the API route above.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
