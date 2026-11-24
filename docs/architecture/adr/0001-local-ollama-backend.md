# ADR 0001: Local Ollama backend on the CPU

## Status

Accepted (commit `ec73e70`, 2026-11-15).

## Context

The project measures how well a small open model rewrites Polish text into PK on commodity hardware. The measurement must not depend on a hosted model service.

## Decision

The rewrite core calls a local Ollama server over HTTP (`POST /api/chat`, `stream: false`, `think: false`) with fixed sampling options and `seed` 42. The server address comes from `OLLAMA_URL` (default `http://127.0.0.1:11434`). The accepted models come from `PK_MODELS` (default `qwen3.5:4b,qwen3.5:2b,qwen3.5:0.8b`).

## Consequences

- Text never leaves the machine or the Compose network.
- Speed depends on the CPU and on other load; the README treats the measured speeds as lower bounds.
- The same seed does not give the same answer in every run: the README reports that Ollama gave other samples for the same prompt and seed in a second run.

## Evidence

- `pk_rewriter/rewrite.py`: `OLLAMA_URL`, `OPTIONS`, `MODELS`, `chat`.
- `compose.yaml`: service `ollama` with image `ollama/ollama:0.34.1`.
- Commit `ec73e70` "Add Ollama rewrite loop: generate, check with pklint and numbers, repair".
