# Machine

Every number in this repository comes from one laptop. `scripts/machine.sh` prints the table below; it reads `/proc`, `/sys`, `lspci`, `lsblk` and the Ollama API, and prints no serial number, host name, address or user path.

| Part | Value |
|---|---|
| Computer | LENOVO ThinkPad T470p (type 20J7) |
| CPU | Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz, 4 cores, 8 threads, avx2 fma |
| RAM | 31.1 GiB |
| Disk | SSDPR-PX500-01T-80-G2 953.9G |
| GPU | Intel Corporation Kaby Lake-H GT2 [HD Graphics 630] (rev 04); NVIDIA Corporation GM108M [GeForce 940MX] (rev a2); NVIDIA driver 470.256.02 |
| Operating system | Artix Linux, kernel 7.2.9-artix1-1, init runit |
| Ollama | 0.34.1 |

## Where the model runs: CPU only

Ollama 0.34.1 ran every model on the CPU. The GeForce 940MX (2 GB VRAM, NVIDIA driver 470) is visible to the kernel, but Ollama does not list it as an inference device. Evidence from the Ollama server log and API, 2026-11-15:

```
msg="inference compute" id=cpu library=cpu compute="" name=cpu description=cpu ... total="31.1 GiB" available="8.5 GiB"
msg="vram-based default context" total_vram="0 B" default_num_ctx=4096
load_tensors:          CPU model buffer size =   763.78 MiB      (qwen3.5:0.8b)
llama_kv_cache:        CPU KV buffer size =    48.00 MiB
GET /api/ps  ->  "size_vram": 0
```

Model placement in the log of each evaluation run (`load_tensors`, `llama threadpool`):

| Model | Ollama quantisation | Weights in RAM | Speculative decoding | Threads |
|---|---|---|---|---|
| qwen3.5:0.8b | Q8_0 | CPU buffer 763.78 MiB, MTP draft 278.40 MiB | `draft-mtp`, 2 draft tokens | 4 |
| qwen3.5:2b | Q8_0 | CPU buffer 1908.35 MiB | none | 4 |
| qwen3.5:4b | Q4_K_M | CPU buffer 816.69 MiB, `CPU_REPACK` 1698.75 MiB | none | 4 |

The Ollama library models carry default parameters that the client does not override: `presence_penalty` 1.5 for all 3 models (`ollama show <model> --parameters`). The client sets `temperature`, `top_p`, `top_k`, `seed`, `num_ctx` and `num_predict`.

## Speed

| Model | Tokens per second | Seconds per text | Run (2026-11-15) | 1-minute load average at start and end |
|---|---|---|---|---|
| qwen3.5:0.8b | 7.3 | 27.66 | 14:05:56 to 14:26:13 | 9.92 and 16.47 |
| qwen3.5:2b | 7.6 | 46.16 | 15:40:54 to 16:15:18 | 11.61 and 9.80 |
| qwen3.5:4b | 5.1 | 44.4 | 15:08:07 to 15:40:54 | 3.85 and 11.61 |

Tokens per second is `eval_count` divided by `eval_duration` (both from the Ollama response), summed over every model call of the evaluation. Seconds per text is the wall-clock time of the whole loop for 1 text, at most 3 model calls. Only qwen3.5:0.8b ran with a speculative-decoding draft (`draft-mtp`); its speed includes that optimisation.

The laptop ran a desktop session during the evaluation (browser, chat client). The 1-minute load average on the 8 hardware threads was from 3.85 to 16.47 (`uptime` before and after each run), so the speed is a lower bound for an idle machine of this type, and the speeds of the 3 models are not comparable with each other: qwen3.5:0.8b ran under the highest load. A single short call of qwen3.5:0.8b at 13:55, with a load average of 5.55, generated 9 tokens in 0.52 s (17 tokens per second).
