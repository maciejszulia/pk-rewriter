# ADR 0005: LoRA adapter through `transformers`, not Ollama

## Status

Accepted (commits `66b3d01` and `5d78aef`, 2026-11-15).

## Context

`pk-lora` is a LoRA adapter for Qwen3.5-0.8B, trained on the laptop CPU. Ollama 0.34.1 refuses LoRA adapters (`Error: LoRA adapters are no longer supported`).

## Decision

Training (`models/pk-lora/train.py`, PyTorch with `peft`) and evaluation (`models/pk-lora/eval_hf.py`) run through `transformers` on the CPU in float32. The evaluation keeps the test set, the loop and the metrics of `eval/run_eval.py`; only the model call differs. `pk-qwen` stays an Ollama model (`models/pk-qwen/Modelfile`).

## Consequences

- The speeds of the two backends are not comparable.
- The training dependencies are outside `pyproject.toml`; `models/pk-lora/README.md` lists the install commands.
- The adapter directory is in `.gitignore`.

## Evidence

- `models/pk-lora/train.py`, `models/pk-lora/eval_hf.py` (docstrings).
- `README.md`, section "Models".
- Commit `7f16da0` "docs: models in both READMEs, pk-qwen evaluation, adapter refusal in Ollama, speeds".
