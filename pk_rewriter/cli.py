"""Command line: python -m pk_rewriter [--model M] [--rounds N] [TEXT]; reads stdin without TEXT."""

from __future__ import annotations

import argparse
import sys

from . import rewrite


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m pk_rewriter", description="Rewrite Polish text into PK.")
    ap.add_argument("text", nargs="?", help="text to rewrite; stdin when omitted")
    ap.add_argument("--model", default="qwen3.5:4b")
    ap.add_argument("--rounds", type=int, choices=range(1, rewrite.MAX_ROUNDS + 1), default=rewrite.MAX_ROUNDS)
    args = ap.parse_args(argv)
    text = (args.text if args.text is not None else sys.stdin.read()).strip()
    if not text:
        ap.error("empty text")
    try:
        result = rewrite.rewrite(text, args.model, args.rounds)
    except OSError as e:
        ap.exit(2, f"Ollama call failed: {e}\n")
    print(result["text"])
    for i, rnd in enumerate(result["history"], 1):
        print(f"round {i}: {len(rnd['violations'])} violations, missing numbers: {rnd['missing_numbers'] or '-'}",
              file=sys.stderr)
        for v in rnd["violations"]:
            print(f"  {v['code']} {v['what']}: {v['sentence']}", file=sys.stderr)
    return 0 if result["ok"] else 1
