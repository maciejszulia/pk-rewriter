"""Evaluate Qwen3.5-0.8B through transformers (CPU, float32), with or without the PK LoRA adapter.

Same 44 test texts, loop and metrics as eval/run_eval.py; only the model call differs: transformers
`generate` with the sampling options of pk_rewriter (temperature 0.7, top_p 0.8, top_k 20, seed 42 before
every call, at most 1024 new tokens). The system prompt is the short one of train.py.

Usage: python models/pk-lora/eval_hf.py BASE_DIR NAME [--adapter DIR]
Writes eval/results/<NAME>.jsonl; `python eval/run_eval.py --summary` adds it to the summary.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[1] / "eval"))
sys.path.insert(0, str(HERE))
import run_eval  # noqa: E402
from pk_rewriter import rewrite as rw  # noqa: E402
from train import SHORT, prompt_text  # noqa: E402


def make_chat(model, tok):
    def chat(_name, messages):
        ids = tok(prompt_text(tok, messages), return_tensors="pt", add_special_tokens=False).input_ids
        torch.manual_seed(rw.OPTIONS["seed"])
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(ids, do_sample=True, temperature=rw.OPTIONS["temperature"], top_p=rw.OPTIONS["top_p"],
                                 top_k=rw.OPTIONS["top_k"], max_new_tokens=rw.OPTIONS["num_predict"])
        new = out[0, ids.shape[1]:]
        return {"message": {"content": tok.decode(new, skip_special_tokens=True)},
                "prompt_eval_count": ids.shape[1], "eval_count": int(new.shape[0]),
                "eval_duration": int((time.perf_counter() - t0) * 1e9)}
    return chat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("name")
    ap.add_argument("--adapter")
    args = ap.parse_args()
    torch.set_num_threads(4)
    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.float32)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    rw.chat = make_chat(model, tok)
    return run_eval.run(args.name, system=SHORT, name=args.name, ollama=False)


if __name__ == "__main__":
    sys.exit(main())
