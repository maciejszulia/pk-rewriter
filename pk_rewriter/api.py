"""HTTP API: POST /rewrite, POST /lint, GET /health, GET / (web page)."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StringConstraints, field_validator

from . import pklint, rewrite

MODELS = [m.strip() for m in os.environ.get("PK_MODELS", "qwen3.5:4b,qwen3.5:2b,qwen3.5:0.8b").split(",") if m.strip()]
INDEX = Path(__file__).resolve().parent.parent / "web" / "index.html"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

app = FastAPI(title="pk-rewriter")


class LintIn(BaseModel):
    text: Text


class RewriteIn(LintIn):
    model: str = Field(default_factory=lambda: MODELS[0])
    rounds: int = Field(rewrite.MAX_ROUNDS, ge=1, le=rewrite.MAX_ROUNDS)

    @field_validator("model")
    @classmethod
    def known_model(cls, v):
        if v not in MODELS:
            raise ValueError(f"model must be one of {MODELS}")
        return v


@app.post("/rewrite")
def post_rewrite(body: RewriteIn):
    try:
        return rewrite.rewrite(body.text, body.model, body.rounds)
    except OSError as e:  # URLError, timeouts, refused connections
        raise HTTPException(502, f"Ollama call failed: {e}") from e


@app.post("/lint")
def post_lint(body: LintIn):
    _hits, words, n_sentences, _examples = pklint.lint(body.text)
    return {"violations": rewrite.violations(body.text), "words": words, "sentences": n_sentences}


@app.get("/health")
def health():
    try:
        with urllib.request.urlopen(rewrite.OLLAMA_URL + "/api/version", timeout=2) as resp:
            ollama = resp.status == 200
    except OSError:
        ollama = False
    return {"status": "ok", "ollama": ollama, "models": MODELS}


@app.get("/")
def index():
    return FileResponse(INDEX)
