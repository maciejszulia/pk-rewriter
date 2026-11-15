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

The text model is loaded with `AutoModelForCausalLM` (`Qwen3_5ForCausalLM`, `transformers` 5.23.0) in float32; the vision encoder is not loaded. The Gated DeltaNet layers run on the pure-PyTorch fallback of `transformers`, because `flash-linear-attention` and `causal-conv1d` are not installed (the training log says so).

## Method

1. **Data by rejection sampling with a verifier** (`make_data.py`). qwen3.5:4b rewrites sentences of 5 Polish legal acts with the full `pk_rewriter` loop. An attempt is kept only when it passes the verifier (0 pklint violations, no lost number, not empty) and keeps the source content (chrF to the source sentence at least 35).
2. **LoRA on the CPU** (`train.py`). Plain PyTorch loop in float32, AdamW, loss on the answer tokens only, short system prompt: „Przepisz polski tekst na Polszczyznę Kontrolowaną (PK). Odpowiedz tylko tekstem w PK.”
3. **Evaluation before and after** (`eval_hf.py`). The base model and the base model with the adapter run through `transformers` with the same short prompt, the same 44 test texts, the same repair loop and the same metrics as `eval/run_eval.py`.

LoRA settings: rank 16, alpha 32, dropout 0.05, target modules `q_proj`, `k_proj`, `v_proj`, `o_proj`, `in_proj_qkv`, `in_proj_z`, `out_proj`, `gate_proj`, `up_proj`, `down_proj`; the gate projections `in_proj_a` and `in_proj_b` (16 outputs) are left out. AdamW, learning rate 2e-4, gradient accumulation over 4 examples, 3 epochs, 4 CPU threads, seed 42.

## Data

`make_data.py` ran on 2026-11-15 from 16:19:11 to 18:00:13 with a 100-minute limit. It drew a shuffled pool (seed 42) of 1807 legal-act sentences of 6 to 25 words with at least 1 pklint hit and no overlap with the test set, and qwen3.5:4b rewrote the first 96 of them. Every attempt, accepted or not, is in [`data/attempts.jsonl`](data/attempts.jsonl).

| Step | Pairs |
|---|---|
| attempts of qwen3.5:4b | 96 |
| 0 violations after the loop (verifier) | 74 |
| chrF to the source sentence at least 35 | 51 |
| no copy of the prompt placeholder „Jeżeli W, to D.” | 47 |

The 47 training pairs come from the Civil Code (27), the Constitution (9), the Labour Code (7), the Road Traffic Act (3) and the rules of legislative technique (1); 5871 tokens in total with the short prompt. qwen3.5:4b needed 1.79 calls and 63.1 s per sentence on average.

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

Measured on 2026-11-15 on the laptop of [docs/hardware.md](../../docs/hardware.md), CPU only, 4 threads:

| Step | Time | Note |
|---|---|---|
| download of the base model | 15:07 to 15:32, with 1 resumed connection reset | 1.75 GB at the 1.3 MB/s line of the laptop |
| training data (`make_data.py`, qwen3.5:4b in Ollama) | 100.9 min | 96 attempts, 63.1 s each |
| training (`train.py`) | 793 s (13.2 min) | 47 pairs, 3 epochs, 36 optimizer steps, 10,223,616 trainable parameters of 762,616,640 (1.34 %) |
| evaluation of the base model (`eval_hf.py`) | 18:00:24 to 18:11:22 | 44 texts |
| evaluation with the adapter (`eval_hf.py --adapter`) | 18:24:45 to 18:32:10 | 44 texts |

Training loss (mean over the epoch, answer tokens only): 1.82 after the first 4 examples, 1.30 after epoch 1, 0.53 after epoch 2, 0.23 after epoch 3; source: `train_log.jsonl`. The adapter file takes 40.9 MB in float32; it stays out of git (`.gitignore`), because `train.py` rebuilds it in 13 minutes.

## Evaluation

Same 44 test texts, same loop, same metrics as `eval/run_eval.py`; both rows run through `transformers` with the 26-token prompt. Source: `eval/results/qwen3.5-0.8b-hf-short.jsonl` and `eval/results/pk-lora-0.8b.jsonl`, 2026-11-15.

| Model | 0 violations after call 1 (%) | M (%) | Mean rounds | chrF after loop | Seconds per text | Tokens per second | Answers that copy the source |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B, no adapter | 40.9 | 52.3 | 2.09 | 50.44 | 14.73 | 3.5 | 24 of 44 |
| Qwen3.5-0.8B + pk-lora | 77.3 | 84.1 | 1.39 | 41.96 | 9.90 | 3.4 | 1 of 44 |
| for comparison: qwen3.5:4b in Ollama, 586-token prompt | 77.3 | 93.2 | 1.34 | 42.24 | 44.40 | 5.1 | – |

- The adapter raises M from 52.3 % to 84.1 % and the share of clean first answers from 40.9 % to 77.3 %, the level of qwen3.5:4b after 1 call.
- Without the adapter the model mostly copies the input (24 of 44 answers are the source text). A copy keeps chrF high and passes the linter whenever the source already passes it (40.9 % of the test texts), so the higher chrF of the base row is not better rewriting.
- The adapter needs 9.9 s per text against 44.4 s for qwen3.5:4b, but the backends differ (transformers float32 against Ollama Q4_K_M) and the machine load differed, so the time ratio is indicative only.
- Tokens per second in `transformers` is `eval_count` divided by the wall time of `generate`, which includes the prompt; Ollama reports generation time without the prompt.

## Limits

- The verifier sees only the mechanically decidable PK rules. qwen3.5:4b rewrites that pass it can still change the meaning, and the adapter learns those changes too.
- The training set is small (47 pairs), comes from 1 register (legal acts) and from 1 teacher model. There is no validation split; a loss of 0.23 after 3 epochs on 47 pairs suggests memorisation, and only the 44 test texts measure generalisation.
- `transformers` sampling differs from Ollama sampling (no `presence_penalty`, float32 instead of Q8_0), so compare the adapter with the base model of the same backend.
- The adapter learned answers that echo the repair prompt in rare cases (test text A5c: the answer repeats the rule sentence of A5), and answers that change the meaning, like its teacher.
- Ollama 0.34.1 has no `ADAPTER` instruction in its Modelfile reference, so the adapter runs through `transformers` only; importing merged Qwen3.5 Safetensors into Ollama was not tried.

## License

The adapter is a derivative of Qwen3.5-0.8B and is released under Apache-2.0, like the base model. The training sentences come from Polish legal acts published at api.sejm.gov.pl; the rewrites come from qwen3.5:4b (Apache-2.0). The code is part of this repository (MIT).
