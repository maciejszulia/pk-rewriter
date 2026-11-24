# ADR 0002: Generate, check, repair loop

## Status

Accepted (commit `ec73e70`, 2026-11-15).

## Context

A single model answer often breaks PK rules or drops a number of the source text. A human check of each answer is slow and subjective.

## Decision

Each text goes through at most 3 rounds (`MAX_ROUNDS = 3`). A round is one model call and one check: `pklint` violations, numbers of the source missing in the answer (excused by the marker `[DO USTALENIA`), and an empty answer. A round with problems produces a repair prompt that names each code, its description, the sentence and one sentence of the rule. The loop stops at 0 problems. The result is the round with the fewest problems, the earliest on a tie.

## Consequences

- The cost of one text is bounded at 3 model calls.
- The metric rewards answers that pass the linter; a guessed fact passes, because `pklint` cannot see meaning (README, "Limits of the method").
- The same loop serves the command line, the HTTP API, the MCP server, the evaluation and the training-data generation.

## Evidence

- `pk_rewriter/rewrite.py`: `check`, `repair_prompt`, `problems`, `rewrite`.
- `tests/test_rewrite.py`: `test_at_most_3_calls`, `test_fewest_problems_wins`, `test_marker_excuses_missing_numbers`.
