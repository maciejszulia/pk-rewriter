# ADR 0004: API bound to localhost, no authentication

## Status

Accepted (commit `07b24e0`, 2026-11-15).

## Context

The HTTP API starts model calls that took from 9.9 to 46.16 seconds per text in the measurements of `README.md` (section "Results"). The API has no authentication.

## Decision

The Compose file publishes the API port on `127.0.0.1:8000` only. The local run in `README.md` starts `uvicorn` without `--host`. The container runs as the unprivileged user `app` (uid 10001).

## Consequences

- Other hosts cannot reach the API without a change of the port binding.
- Exposure on a network needs an authenticating reverse proxy in front of the API; the repository does not provide one.

## Evidence

- `compose.yaml`: `ports: - "127.0.0.1:8000:8000"`.
- `Dockerfile`: `useradd --create-home --uid 10001 app`, `USER app`.
- `README.md`, section "Run in Docker": "The API listens on `127.0.0.1:8000` only, because it has no authentication."
