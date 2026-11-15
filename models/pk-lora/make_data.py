"""Training pairs for the PK LoRA by rejection sampling with a verifier.

qwen3.5:4b rewrites sentences of 5 Polish legal acts with the full loop of pk_rewriter (system prompt,
pklint, number check, at most 3 calls). Every attempt is stored; train.py keeps only the accepted ones.
Sources: rows of register "akt prawny" in data/corpus.csv (PK repository, commit e5c9248); the PDF text
extraction follows scripts/measure.py of that repository. data/items.csv is the test set: a sentence that
appears in it is dropped, and nothing else is read from it.

Usage: python models/pk-lora/make_data.py [--n 300] [--minutes 90] [--model qwen3.5:4b]
       appends to models/pk-lora/data/attempts.jsonl and resumes from it
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))
from pk_rewriter import pklint, rewrite as rw  # noqa: E402
from run_eval import chrf, mem_available_gib, MIN_FREE_GIB  # noqa: E402

CACHE = Path(os.environ.get("PK_CORPUS_CACHE", Path.home() / ".cache" / "pk-corpus"))
OUT = Path(__file__).resolve().parent / "data" / "attempts.jsonl"


def act_text(url):
    """Plain text of 1 legal act from api.sejm.gov.pl, without page furniture, headings and unit numbers."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".pdf")
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "corpus-statistics/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            path.write_bytes(resp.read())
    text = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, check=True).stdout.decode()
    text = re.sub(r"(?m)^\s*(?:Dziennik Ustaw|©Kancelaria Sejmu).*$", "", text)
    text = re.sub(r"(?m)^\s*[–-]\s*\d+\s*[–-]\s*(?:Poz\.\s*\d+)?\s*$", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text).replace("\f", "\n\n")
    text = re.sub(r"(?m)^\s*(?:Rozdział|DZIAŁ|TYTUŁ|KSIĘGA|Oddział)\b.*$", "", text)
    text = re.sub(r"(?m)^\s*(?:Art\.|§)\s*\d+[a-z]*\.?\s*", "", text)
    return re.sub(r"(?m)^\s*\d+[a-z]?[.)]\s+", "", text)


def candidates(n, seed=42):
    """n sentences of 6 to 25 words that start with a capital letter, end with a dot and break a PK rule."""
    with open(ROOT / "data" / "items.csv", encoding="utf-8") as fh:
        test = {s for row in csv.DictReader(fh) for v in row.values() for s in pklint.sentences(v)}
    pool = set()
    with open(ROOT / "data" / "corpus.csv", encoding="utf-8") as fh:
        for src in csv.DictReader(fh):
            if src["register"] != "akt prawny":
                continue
            for s in pklint.sentences(act_text(src["source"])):
                if (6 <= pklint.n_words(s) <= 25 and re.match(r"[A-ZĄĆĘŁŃÓŚŹŻ]", s) and s.endswith(".")
                        and pklint.lint(s)[0] and s not in test and not any(t in s for t in test if len(t) > 20)):
                    pool.add((src["id"], s))
    pool = sorted(pool)
    random.Random(seed).shuffle(pool)
    return pool[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--minutes", type=float, default=90)
    ap.add_argument("--model", default="qwen3.5:4b")
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        done = {json.loads(line)["source"] for line in OUT.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [c for c in candidates(args.n) if c[1] not in done]
    print(f"{len(done)} done, {len(todo)} to do", flush=True)
    stop = time.monotonic() + 60 * args.minutes
    with open(OUT, "a", encoding="utf-8") as out:
        for act, src in todo:
            if time.monotonic() > stop:
                print("time limit reached", flush=True)
                break
            free = mem_available_gib()
            if free < MIN_FREE_GIB:
                print(f"PAUSED: MemAvailable {free:.1f} GiB < {MIN_FREE_GIB} GiB", flush=True)
                return 3
            t0 = time.perf_counter()
            res = rw.rewrite(src, args.model)
            rec = {"act": act, "source": src, "text": res["text"], "ok": res["ok"], "rounds": res["rounds"],
                   "chrf_source": round(chrf(res["text"], src), 1), "seconds": round(time.perf_counter() - t0, 1),
                   "eval_count": sum(r["eval_count"] for r in res["history"])}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            print(f"{act}: ok={res['ok']} rounds={res['rounds']} chrf={rec['chrf_source']} {rec['seconds']} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
