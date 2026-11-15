#!/usr/bin/env python3
"""Plain prose of a Markdown file for pklint: no code, tables, images, links, HTML or formulas.

Usage: python scripts/pk_text.py README.pl.md > prose.txt && python -m pk_rewriter.pklint prose.txt
"""
import re
import sys


def prose(md):
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"<[^>]+>", "", md)
    md = re.sub(r"\$\$.*?\$\$", " X ", md, flags=re.S)
    md = re.sub(r"\$[^$\n]*\$", "X", md)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    out = []
    for line in md.split("\n"):
        if line.lstrip().startswith("|"):
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
        out.append(line.replace("**", ""))
    return "\n\n".join(out)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        print(prose(fh.read()))
