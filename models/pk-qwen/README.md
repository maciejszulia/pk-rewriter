---
license: apache-2.0
language:
  - pl
base_model: Qwen/Qwen3.5-4B
pipeline_tag: text-generation
tags:
  - ollama
  - polish
  - controlled-language
---

# pk-qwen

An Ollama model that rewrites Polish text into Controlled Polish (PK). It is `qwen3.5:4b` with the PK system prompt of `pk_rewriter/rewrite.py` and the sampling parameters of the project built in, so a client sends only the text: `ollama run pk-qwen "Jeśli pompa stoi, trzeba ją szybko włączyć."`

## Base model

`qwen3.5:4b` from the Ollama library: Qwen3.5-4B ([Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B), Apache-2.0), quantised to Q4_K_M, 4.2B parameters in the language model plus a 333.51M vision projector, 3.3 GB on disk. It has the best M of the 3 evaluated sizes (93.2 %, against 43.2 % for 2B and 50.0 % for 0.8B), so it is the base. The library build also sets `presence_penalty` 1.5, which `pk-qwen` inherits (`ollama show pk-qwen --modelfile`).

## Method

No training. The `Modelfile` adds:

- `SYSTEM`: the 586-token Polish prompt (3 principles of PK, the marker `[DO USTALENIA: czego brakuje]`, key rules, answer format, 2 examples written for this project; no test sentence);
- `PARAMETER`: `temperature` 0.7, `top_p` 0.8, `top_k` 20, `seed` 42, `num_ctx` 4096, `num_predict` 1024.

A unit test (`tests/test_models.py`) fails when the `Modelfile` and the client prompt or options drift apart.

## Data

None for building. Evaluation: the 44 texts of `data/items.csv` (PK repository, commit `e5c9248`).

## Build and run

```sh
ollama create pk-qwen -f models/pk-qwen/Modelfile
ollama run pk-qwen "Jeśli pompa stoi, trzeba ją szybko włączyć."
python eval/run_eval.py pk-qwen --no-system     # the loop sends no system prompt; the model has it
```

## Time on this machine

`ollama create pk-qwen -f models/pk-qwen/Modelfile` took 0.14 s on 2026-11-15: Ollama reuses the weight blobs of `qwen3.5:4b` and writes 1 new layer for the prompt and the parameters.

## Evaluation

Pending: `python eval/run_eval.py pk-qwen --no-system` runs after the LoRA experiment; the result goes to `eval/results/pk-qwen.jsonl` and to the summary.

## Limits

- `ollama run` gives 1 answer; the repair loop with pklint runs only through `pk_rewriter` (API, command line, `run_eval.py`).
- The limits of the method in the main [README](../../README.md#limits-of-the-method) apply: pklint checks only the mechanically decidable PK rules.

## License

The weights are Qwen3.5-4B under Apache-2.0 ([license](https://huggingface.co/Qwen/Qwen3.5-4B/blob/main/LICENSE)). The `Modelfile` and the prompt are part of this repository (MIT).
