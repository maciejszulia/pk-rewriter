"""LoRA on a CPU for the text part of Qwen3.5-0.8B (plain PyTorch loop, peft adapter).

Data: attempts of make_data.py that passed the verifier (ok), keep the source content (chrF to the
source >= 35) and do not copy the placeholder pattern of the system prompt ("Jeżeli W, to D.").
Chat: short PK system prompt, user = legal sentence, assistant = PK rewrite of qwen3.5:4b.
The loss covers the answer tokens only.

Usage: python models/pk-lora/train.py BASE_DIR [--epochs 3] [--rank 16] [--lr 2e-4] [--accum 4]
Writes models/pk-lora/adapter/ (after every epoch) and models/pk-lora/train_log.jsonl.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "eval"))
from run_eval import mem_available_gib, MIN_FREE_GIB  # noqa: E402

SHORT = "Przepisz polski tekst na Polszczyznę Kontrolowaną (PK). Odpowiedz tylko tekstem w PK."
MIN_CHRF = 35.0
# Full-attention, Gated DeltaNet and MLP projections of the text model. The gate projections in_proj_a and
# in_proj_b map to 16 outputs only, so a rank-16 adapter would not be low-rank there.
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "in_proj_z", "out_proj",
           "gate_proj", "up_proj", "down_proj"]


def pairs():
    lines = (HERE / "data" / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
    recs = [json.loads(line) for line in lines if line.strip()]
    return [(r["source"], r["text"]) for r in recs
            if r["ok"] and r["chrf_source"] >= MIN_CHRF and "W, to D" not in r["text"]]


def prompt_text(tok, messages):
    return tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False, enable_thinking=False)


def encode(tok, source, answer):
    prompt = tok(prompt_text(tok, [{"role": "system", "content": SHORT}, {"role": "user", "content": source}]),
                 add_special_tokens=False).input_ids
    target = tok(answer + "<|im_end|>", add_special_tokens=False).input_ids
    return torch.tensor(prompt + target), torch.tensor([-100] * len(prompt) + target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--accum", type=int, default=4)
    args = ap.parse_args()
    torch.manual_seed(42)
    torch.set_num_threads(4)
    tok = AutoTokenizer.from_pretrained(args.base)
    data = [encode(tok, s, a) for s, a in pairs()]
    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.float32)   # text part only
    names = {n.rsplit(".", 1)[-1] for n, m in model.named_modules() if isinstance(m, torch.nn.Linear)}
    targets = sorted(names & set(TARGETS))
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
                                             target_modules=targets, task_type="CAUSAL_LM"))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log = open(HERE / "train_log.jsonl", "a", encoding="utf-8")
    meta = {"examples": len(data), "tokens": sum(len(x) for x, _ in data), "targets": targets,
            "trainable": trainable, "total": total, **vars(args)}
    print(json.dumps(meta), flush=True)
    log.write(json.dumps({"start": time.strftime("%Y-%m-%d %H:%M:%S"), **meta}) + "\n")
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0)
    model.train()
    step, t0 = 0, time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        order = list(range(len(data)))
        random.Random(epoch).shuffle(order)
        total_loss = 0.0
        for i, k in enumerate(order, 1):
            if mem_available_gib() < MIN_FREE_GIB:
                print(f"PAUSED: MemAvailable < {MIN_FREE_GIB} GiB", flush=True)
                model.save_pretrained(HERE / "adapter")
                return 3
            ids, labels = data[k]
            loss = model(input_ids=ids[None], labels=labels[None]).loss
            (loss / args.accum).backward()
            total_loss += loss.item()
            if i % args.accum == 0 or i == len(order):
                opt.step()
                opt.zero_grad()
                step += 1
                rec = {"epoch": epoch, "step": step, "example": i, "loss": round(total_loss / i, 4),
                       "seconds": round(time.perf_counter() - t0, 1), "free_gib": round(mem_available_gib(), 1)}
                print(json.dumps(rec), flush=True)
                log.write(json.dumps(rec) + "\n")
                log.flush()
        model.save_pretrained(HERE / "adapter")
    log.write(json.dumps({"end": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.perf_counter() - t0, 1)}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
