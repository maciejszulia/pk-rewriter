# Hugging Face research for pk-rewriter

Checked on 2026-11-15 through the public Hugging Face Hub API (no account, no token), model cards, `config.json` files and the documentation pages linked below. Download counts change daily; they show popularity on the day of the check, nothing more.

Queries used (all anonymous `GET` requests):

- `https://huggingface.co/api/models?author=Qwen&search=Qwen3.5&sort=downloads`
- `https://huggingface.co/api/models/<id>` for every model in the tables
- `https://huggingface.co/api/models?author=speakleash&sort=downloads`, `...?author=CYFRAGOVPL&sort=downloads`
- `https://huggingface.co/api/models?search=<polish qwen | qwen pl | qwen-polish | polish-qwen>`
- `https://huggingface.co/api/datasets?search=<polish instruct | text simplification | plain language | polish legal>` and `...?filter=language:pl&filter=task_categories:text-generation`

## 1. Qwen3.5 and Qwen3 from 0.6B to 4B

| Model | Parameters (safetensors) | Architecture | Input | License |
|---|---|---|---|---|
| [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) | 873,438,784 | `Qwen3_5ForConditionalGeneration` | image, video, text | Apache-2.0 |
| [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | 2,274,069,824 | `Qwen3_5ForConditionalGeneration` | image, video, text | Apache-2.0 |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | 4,659,865,088 | `Qwen3_5ForConditionalGeneration` | image, video, text | Apache-2.0 |
| [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) | 751,632,384 | `Qwen3ForCausalLM` | text | Apache-2.0 |
| [Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) | 2,031,739,904 | `Qwen3ForCausalLM` | text | Apache-2.0 |
| [Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | 4,022,468,096 | `Qwen3ForCausalLM` | text | Apache-2.0 |

Findings:

- Every small Qwen3.5 model is multimodal (pipeline `image-text-to-text`); the parameter counts include the vision encoder. The Hub also lists `-Base` variants (pre-trained only) of 0.8B, 2B and 4B.
- The text part of [Qwen3.5-0.8B `config.json`](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/config.json) is a hybrid: 24 layers in the pattern 3 × `linear_attention` + 1 × `full_attention`, hidden size 1024, 8 query heads and 2 key-value heads in the full-attention layers, vocabulary 248,320, tied embeddings, 1 multi-token-prediction (MTP) layer. The vision encoder has 12 layers. The weights are stored in bfloat16.
- The config was written by `transformers` 4.57.0.dev0, so Qwen3.5 needs a `transformers` release with the `qwen3_5` model type ([model documentation](https://huggingface.co/docs/transformers/main/en/model_doc/qwen3_5)). Qwen3 (dense transformer, text only) works with older releases.
- `transformers` 5.23.0 maps `qwen3_5` to `Qwen3_5ForCausalLM` for text-only loading and has a pure-PyTorch fallback (`torch_chunk_gated_delta_rule`) for the Gated DeltaNet layers when `flash-linear-attention` is missing, so the model runs on a CPU. `peft` LoRA wraps `torch.nn.Linear` layers; the Linear layers of the text model are `q_proj`, `k_proj`, `v_proj`, `o_proj` (full attention), `in_proj_qkv`, `in_proj_z`, `in_proj_a`, `in_proj_b`, `out_proj` (Gated DeltaNet) and `gate_proj`, `up_proj`, `down_proj` (MLP); checked in the source of `transformers/models/qwen3_5/modeling_qwen3_5.py`.
- Ollama serves `qwen3.5:0.8b`, `qwen3.5:2b`, `qwen3.5:4b`, `qwen3:0.6b` and `qwen3:1.7b` (registry manifests answer HTTP 200). The Ollama library build of `qwen3.5:0.8b` carries an MTP draft (`draft_num_predict 2`, `draft-mtp` in the server log), so Ollama decodes it speculatively; the 2B and 4B builds load without a draft.

## 2. Polish models

| Model | Parameters | Architecture | License | Access |
|---|---|---|---|---|
| [speakleash/Bielik-1.5B-v3.0-Instruct](https://huggingface.co/speakleash/Bielik-1.5B-v3.0-Instruct) | 1,596,507,648 | `LlamaForCausalLM` | Apache-2.0 | gated (accept terms while logged in) |
| [speakleash/Bielik-4.5B-v3.0-Instruct](https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct) | 4,757,260,288 | `LlamaForCausalLM` | Apache-2.0 | gated |
| [speakleash/Bielik-11B-v3.0-Instruct](https://huggingface.co/speakleash/Bielik-11B-v3.0-Instruct) | 11,168,796,672 | `LlamaForCausalLM` | Apache-2.0 | gated |
| [CYFRAGOVPL/PLLuM-4B-instruct-2512](https://huggingface.co/CYFRAGOVPL/PLLuM-4B-instruct-2512) | 4,299,923,312 | `Gemma3ForConditionalGeneration` | Apache-2.0 | open |
| [speakleash/Bielik-Guard-0.5B-v1.1](https://huggingface.co/speakleash/Bielik-Guard-0.5B-v1.1) | 442,895,365 | `RobertaForSequenceClassification` | Apache-2.0 | gated |

Findings:

- Bielik v3 (SpeakLeash) is the main Polish open family; the 1.5B and 4.5B instruct models also ship as GGUF files. The PK repository already measured Bielik 1.5B and 4.5B through Ollama (`results/probe_ollama_speakleash-bielik-*.jsonl` there). The Hugging Face weights are gated, and this project uses no account, so Bielik stays out of the training experiments.
- PLLuM (the Polish government consortium, CYFRAGOVPL) publishes 4B, 8B, 12B, 8x7B and 70B models; the 4B instruct model is built on the Gemma 3 architecture and is not gated, but it is larger than the CPU budget of this project allows for training.
- Bielik-Guard is a safety classifier, not a generator.
- Searches for Polish instruction fine-tunes of Qwen3 or Qwen3.5 from 0.6B to 4B returned none (the results were unrelated names that contain "polished"). A small Qwen adapted to Polish controlled language is therefore a gap.

## 3. Polish datasets for instructions and text simplification

| Dataset | Content | License |
|---|---|---|
| [JohnTdi/polish-llm-sft-pl](https://huggingface.co/datasets/JohnTdi/polish-llm-sft-pl) | Polish supervised fine-tuning data, 10K–100K rows | Apache-2.0 |
| [s3nh/alpaca-dolly-instruction-only-polish](https://huggingface.co/datasets/s3nh/alpaca-dolly-instruction-only-polish) | Alpaca and Dolly instructions in Polish | not stated |
| [speakleash/PES-2018-2022](https://huggingface.co/datasets/speakleash/PES-2018-2022) | Polish texts, 10K–100K rows | see card |
| [czlonkowski/polish-tax-interpretations](https://huggingface.co/datasets/czlonkowski/polish-tax-interpretations) | official tax interpretations in Polish | CC-BY-4.0 |
| [wikimedia/wikipedia](https://huggingface.co/datasets/wikimedia/wikipedia), [HPLT/HPLT2.0_cleaned](https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned), [epfml/FineWeb2-HQ](https://huggingface.co/datasets/epfml/FineWeb2-HQ) | large web and encyclopedia corpora with Polish subsets | CC-BY-SA-3.0, CC0-1.0, ODC-By |

Findings:

- No Polish text-simplification or controlled-language dataset exists on the Hub: the query "simplification" with `language:pl` returned 0 datasets; "text simplification" returned English, Estonian, Brazilian Portuguese and Arabic sets only.
- Pairs "Polish text → PK" therefore have to be generated. The PK linter is a verifier, so synthetic pairs can be filtered automatically. Official Polish (legal acts, tax interpretations) is the natural source of sentences, because it breaks many PK rules.

## 4. Fine-tuning methods that run on a CPU

| Method | Source | Fit for this project |
|---|---|---|
| LoRA | [Hu et al., 2021](https://huggingface.co/papers/2106.09685); [PEFT LoRA guide](https://huggingface.co/docs/peft/main/en/developer_guides/lora) | Trains low-rank adapters only; float32 on a CPU needs the base weights plus a small optimizer state. Used. |
| QLoRA | [Dettmers et al., 2023](https://huggingface.co/papers/2305.14314); [bitsandbytes installation](https://huggingface.co/docs/bitsandbytes/main/en/installation) | bitsandbytes ships CPU wheels (Linux x86-64, AVX2 minimum). A 4-bit base saves memory, but a 0.8B model fits in float32, and dequantisation costs CPU time. Not used. |
| Rejection-sampling fine-tuning | [Yuan et al., 2023 (RFT)](https://huggingface.co/papers/2308.01825); [STaR](https://huggingface.co/papers/2203.14465); [ReST](https://huggingface.co/papers/2308.08998) | Generate candidates, keep the ones a verifier accepts, fine-tune on them. pklint plus the number check is the verifier. Used for the training data. |
| Supervised fine-tuning | [TRL SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) | The training loop of `models/pk-lora/train.py` is a minimal version of this (loss on the answer tokens only), in plain PyTorch. |
| GRPO with a verifier reward | [DeepSeekMath, Shao et al., 2024](https://huggingface.co/papers/2402.03300); [TRL GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) | Online reinforcement learning: several samples per prompt and step, reward = fewer pklint violations and no lost number. Each step needs several generations, which take minutes on this CPU. Left as the next step. |

## 5. Decisions

1. **pk-qwen** (Ollama `Modelfile`): the Qwen3.5 size with the best M in the evaluation, with the PK system prompt and the sampling parameters built in. No training; the client sends only the text.
2. **pk-lora** (LoRA adapter): base Qwen3.5-0.8B, not 2B. Float32 weights take 3.5 GB for 0.8B and 9.1 GB for 2B (vision encoder included); the machine had 8 GiB to 9 GiB of available memory, so training 2B would cross the 2 GiB floor of this project. 0.8B is also the weakest model in the evaluation, so an adapter has the most room to help. Data: rejection sampling of qwen3.5:4b rewrites of legal-act sentences, verified by pklint and the number check; the test set is never used.
3. The Ollama Modelfile reference (checked 2026-11-15, [docs.ollama.com/modelfile](https://docs.ollama.com/modelfile)) lists `FROM`, `PARAMETER`, `TEMPLATE`, `SYSTEM`, `LICENSE` and `MESSAGE`, and no `ADAPTER`; [importing](https://docs.ollama.com/import) accepts Safetensors weights "for a supported architecture". The adapter is therefore merged into the base and the merged weights are offered to `ollama create`; when Ollama refuses them, the model is measured through `transformers`.
