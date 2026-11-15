---
license: apache-2.0
language:
  - pl
base_model: Qwen/Qwen3.5-0.8B
library_name: peft
pipeline_tag: text-generation
tags:
  - lora
  - polish
  - controlled-language
  - rejection-sampling
---

# pk-lora

A LoRA adapter for Qwen3.5-0.8B that rewrites Polish text into Controlled Polish (PK) with a 26-token system prompt instead of the 586-token prompt of `pk_rewriter`. It was trained on a laptop CPU, on rewrites of legal-act sentences that qwen3.5:4b produced and the PK linter accepted.

## Base model

[Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B), revision `2fc06364715b967f1860aea9cf38778875588b17`, Apache-2.0. Why 0.8B and not 2B: see [docs/research-huggingface.md](../../docs/research-huggingface.md#5-decisions).

The text model is loaded with `AutoModelForCausalLM` (`Qwen3_5ForCausalLM`, `transformers` 5.23.0) in float32; the vision encoder is not loaded. The Gated DeltaNet layers run on the pure-PyTorch fallback of `transformers`, because `flash-linear-attention` and `causal-conv1d` need a GPU build.

## Method

1. **Data by rejection sampling with a verifier** (`make_data.py`). qwen3.5:4b rewrites sentences of 5 Polish legal acts with the full `pk_rewriter` loop. An attempt is kept only when it passes the verifier (0 pklint violations, no lost number, not empty) and keeps the source content (chrF to the source sentence at least 35).
2. **LoRA on the CPU** (`train.py`). Plain PyTorch loop in float32, AdamW, loss on the answer tokens only, short system prompt: „Przepisz polski tekst na Polszczyznę Kontrolowaną (PK). Odpowiedz tylko tekstem w PK.”
3. **Evaluation before and after** (`eval_hf.py`). The base model and the base model with the adapter run through `transformers` with the same short prompt, the same 44 test texts, the same repair loop and the same metrics as `eval/run_eval.py`.

LoRA settings: rank 16, alpha 32, dropout 0.05, target modules `q_proj`, `k_proj`, `v_proj`, `o_proj`, `in_proj_qkv`, `in_proj_z`, `out_proj`, `gate_proj`, `up_proj`, `down_proj`; the gate projections `in_proj_a` and `in_proj_b` (16 outputs) are left out. AdamW, learning rate 2e-4, gradient accumulation over 4 examples, 3 epochs, 4 CPU threads, seed 42.

## Data

Pending: `make_data.py` runs on 2026-11-15 from 16:19 for 100 minutes; every attempt, accepted or not, is stored in `data/attempts.jsonl`.

## Commands

```sh
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install transformers peft accelerate
models/pk-lora/download_base.sh                                   # 1.8 GB to ~/.cache/pk-rewriter/Qwen3.5-0.8B
python models/pk-lora/make_data.py --n 300 --minutes 75          # needs Ollama with qwen3.5:4b
python models/pk-lora/eval_hf.py ~/.cache/pk-rewriter/Qwen3.5-0.8B qwen3.5-0.8b-hf-short
python models/pk-lora/train.py ~/.cache/pk-rewriter/Qwen3.5-0.8B
python models/pk-lora/eval_hf.py ~/.cache/pk-rewriter/Qwen3.5-0.8B pk-lora-0.8b --adapter models/pk-lora/adapter
python eval/run_eval.py --summary
```

## Time on this machine

Pending: measured during the run.

## Evaluation

Pending: measured during the run.

## Limits

- The verifier sees only the mechanically decidable PK rules. qwen3.5:4b rewrites that pass it can still change the meaning, and the adapter learns those changes too.
- The training set is small (the number of accepted pairs is in the Data section), comes from 1 register (legal acts) and from 1 teacher model.
- `transformers` sampling differs from Ollama sampling (no `presence_penalty`, float32 instead of Q8_0), so compare the adapter with the base model of the same backend.

## License

The adapter is a derivative of Qwen3.5-0.8B and is released under Apache-2.0, like the base model. The training sentences come from Polish legal acts published at api.sejm.gov.pl; the rewrites come from qwen3.5:4b (Apache-2.0). The code is part of this repository (MIT).
