# ADR 0003: Vendored `pklint`

## Status

Accepted (commit `a0b819a`, 2026-11-15).

## Context

The PK rules and their linter live in the PK repository. The rewrite loop needs the linter at run time, and the evaluation needs the test set of the same version.

## Decision

`pk_rewriter/pklint.py` is a verbatim copy of `src/pklint.py` from the PK repository at commit `e5c9248`; only a source comment is added. `data/items.csv` comes from the same commit.

## Consequences

- The package has no dependency on the PK repository at install or run time.
- The rules and the test set are pinned to one version, so results stay comparable.
- A fix in the PK repository needs a new copy here.

## Evidence

- Header of `pk_rewriter/pklint.py`: "Verbatim copy; only this comment is added."
- Commit `a0b819a` "Add pklint and the 44-item test set from the PK repository (commit e5c9248)".
