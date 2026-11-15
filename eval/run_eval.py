"""Evaluate pk-rewriter on data/items.csv: 44 Polish texts with 2 reference rewrites in PK each.

Source of data/items.csv: github.com/maciejszulia/polszczyzna-kontrolowana, commit e5c9248.
Input is the column `nat`, references are the columns `pk1` and `pk2`.

Usage:
    python eval/run_eval.py MODEL      run one model; resumes from eval/results/<model>.jsonl
    python eval/run_eval.py MODEL --no-system   send no system prompt (model with a built-in one)
    python eval/run_eval.py --summary  write summary.json, summary.md and summary.png
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pk_rewriter import rewrite as rw  # noqa: E402

ITEMS = ROOT / "data" / "items.csv"
RESULTS = ROOT / "eval" / "results"
MIN_FREE_GIB = 2.0


def items():
    with open(ITEMS, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def chrf(hyp, ref, order=6, beta=2.0):
    """chrF: character n-grams of order 1..6 without whitespace, mean precision and mean recall, F-beta."""
    hyp, ref = "".join(hyp.split()), "".join(ref.split())
    precisions, recalls = [], []
    for n in range(1, order + 1):
        h = Counter(hyp[i:i + n] for i in range(len(hyp) - n + 1))
        r = Counter(ref[i:i + n] for i in range(len(ref) - n + 1))
        if not h or not r:
            continue
        match = sum((h & r).values())
        precisions.append(match / sum(h.values()))
        recalls.append(match / sum(r.values()))
    if not precisions:
        return 0.0
    p, r = sum(precisions) / len(precisions), sum(recalls) / len(recalls)
    return 0.0 if p + r == 0 else 100 * (1 + beta**2) * p * r / (beta**2 * p + r)


def mem_available_gib():
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 2**20
    except OSError:
        pass
    return float("inf")


def result_path(model):
    return RESULTS / (model.replace(":", "-").replace("/", "-") + ".jsonl")


def ollama_post(path, body):
    req = urllib.request.Request(rw.OLLAMA_URL + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def run(model, system=rw.SYSTEM, name=None, ollama=True):
    """name labels the result file and the summary row; ollama=False skips loading and unloading."""
    name = name or model
    path = result_path(name)
    done = set()
    if path.exists():
        done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [it for it in items() if it["id"] not in done]
    print(f"{name}: {len(done)} done, {len(todo)} to do", flush=True)
    if not todo:
        return 0
    if ollama:
        ollama_post("/api/chat", {"model": model, "messages": [{"role": "user", "content": "OK"}], "stream": False,
                                  "think": False, "options": {"num_predict": 1}})   # load the model before timing
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as out:
        for it in todo:
            free = mem_available_gib()
            if free < MIN_FREE_GIB:
                print(f"PAUSED: MemAvailable {free:.1f} GiB < {MIN_FREE_GIB} GiB", flush=True)
                return 3
            t0 = time.perf_counter()
            res = rw.rewrite(it["nat"], model, system=system)
            sec = time.perf_counter() - t0
            out.write(json.dumps({"id": it["id"], "model": name, "nat": it["nat"], "seconds": round(sec, 2), **res},
                                 ensure_ascii=False) + "\n")
            out.flush()
            print(f"{it['id']}: ok={res['ok']} rounds={res['rounds']} {sec:.1f} s free={free:.1f} GiB", flush=True)
    if ollama:
        ollama_post("/api/generate", {"model": model, "keep_alive": 0})   # unload: 1 model in RAM at a time
    return 0


def is_clean(source, text):
    found, missing = rw.check(source, text)
    return bool(text) and not found and not missing


def pct(flags):
    return round(100 * sum(flags) / len(flags), 1)


def mean(xs):
    return round(sum(xs) / len(xs), 2)


def size_key(model):
    m = re.search(r":(\d+(?:\.\d+)?)b", model)
    return float(m.group(1)) if m else 0.0


def summarize():
    refs = {it["id"]: it for it in items()}
    best_ref = lambda rid, text: max(chrf(text, refs[rid]["pk1"]), chrf(text, refs[rid]["pk2"]))  # noqa: E731
    rows = [{"model": "source text (nat), no model", "n": len(refs),
             "clean_first_pct": pct([is_clean(it["nat"], it["nat"]) for it in refs.values()]),
             "clean_loop_pct": None, "mean_rounds": None,
             "chrf_first": mean([best_ref(i, it["nat"]) for i, it in refs.items()]), "chrf_loop": None,
             "sec_per_text": None, "tok_per_sec": None}]
    for path in RESULTS.glob("*.jsonl"):
        recs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rounds = [r for rec in recs for r in rec["history"]]
        rows.append({
            "model": recs[0]["model"], "n": len(recs),
            "clean_first_pct": pct([rw.problems(rec["history"][0]) == 0 for rec in recs]),
            "clean_loop_pct": pct([rec["ok"] for rec in recs]),
            "mean_rounds": mean([rec["rounds"] for rec in recs]),
            "chrf_first": mean([best_ref(rec["id"], rec["history"][0]["text"]) for rec in recs]),
            "chrf_loop": mean([best_ref(rec["id"], rec["text"]) for rec in recs]),
            "sec_per_text": mean([rec["seconds"] for rec in recs]),
            "tok_per_sec": round(sum(r["eval_count"] for r in rounds) / max(sum(r["eval_seconds"] for r in rounds), 1e-9), 1),
            "pklint_clean_first_pct": pct([not rec["history"][0]["violations"] for rec in recs]),
            "pklint_clean_loop_pct": pct([not rw.violations(rec["text"]) for rec in recs]),
            "chrf_source_loop": mean([chrf(rec["text"], rec["nat"]) for rec in recs]),
        })
    rows[1:] = sorted(rows[1:], key=lambda r: size_key(r["model"]))
    (RESULTS / "summary.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cols = [("model", "Model"), ("n", "Texts"), ("clean_first_pct", "0 violations after call 1 (%)"),
            ("clean_loop_pct", "0 violations after loop, M (%)"), ("mean_rounds", "Mean rounds"),
            ("chrf_first", "chrF after call 1"), ("chrf_loop", "chrF after loop"),
            ("sec_per_text", "Seconds per text"), ("tok_per_sec", "Tokens per second")]
    md = ["| " + " | ".join(c[1] for c in cols) + " |", "|" + "---|" * len(cols)]
    md += ["| " + " | ".join("–" if r.get(k) is None else str(r[k]) for k, _ in cols) + " |" for r in rows]
    (RESULTS / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if len(rows) > 1:
        chart(rows)
    print("\n".join(md))


def chart(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    base, models = rows[0], rows[1:]
    best = max(models, key=lambda r: r["clean_loop_pct"])
    gain = round(best["clean_loop_pct"] - best["clean_first_pct"], 1)
    title = (f"{best['model']} writes {best['clean_loop_pct']:g} % of texts with 0 violations;"
             f" the repair loop adds {gain:g} pp")
    x = range(len(models))
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for off, key, color, label in ((-0.2, "clean_first_pct", "#2a78d6", "after call 1"),
                                   (0.2, "clean_loop_pct", "#eb6834", "after repair loop (M)")):
        vals = [r[key] for r in models]
        bars = ax.bar([i + off for i in x], vals, width=0.36, color=color, label=label, edgecolor="#fcfcfb", linewidth=2)
        ax.bar_label(bars, labels=[f"{v:g}" for v in vals], padding=2, color="#0b0b0b")
    ax.axhline(base["clean_first_pct"], color="#52514e", linestyle="--", linewidth=1.5,
               label=f"source text, no model: {base['clean_first_pct']:g}")
    ax.set_xticks(list(x), [r["model"] for r in models])
    ax.set_ylabel("texts with 0 violations (%)", color="#52514e")
    ax.set_ylim(0, 100)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title(title, loc="left", fontsize=11, color="#0b0b0b")
    fig.tight_layout()
    fig.savefig(RESULTS / "summary.png", dpi=150, facecolor=fig.get_facecolor())


if __name__ == "__main__":
    if sys.argv[1:] == ["--summary"]:
        summarize()
    elif len(sys.argv) == 2:
        sys.exit(run(sys.argv[1]))
    elif len(sys.argv) == 3 and sys.argv[2] == "--no-system":
        sys.exit(run(sys.argv[1], system=None))
    else:
        sys.exit(__doc__)
