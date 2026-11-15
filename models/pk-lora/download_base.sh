#!/bin/sh
# Download Qwen/Qwen3.5-0.8B (Apache-2.0) from the Hugging Face Hub, pinned revision, no account needed.
# Usage: models/pk-lora/download_base.sh [DIR]   default DIR: ~/.cache/pk-rewriter/Qwen3.5-0.8B (1.8 GB)
set -eu
rev=2fc06364715b967f1860aea9cf38778875588b17
dir=${1:-$HOME/.cache/pk-rewriter/Qwen3.5-0.8B}
mkdir -p "$dir"
for f in LICENSE chat_template.jinja config.json merges.txt model.safetensors-00001-of-00001.safetensors \
         model.safetensors.index.json preprocessor_config.json tokenizer.json tokenizer_config.json \
         video_preprocessor_config.json vocab.json; do
  curl -fsSL --retry 5 --retry-all-errors -C - -o "$dir/$f" "https://huggingface.co/Qwen/Qwen3.5-0.8B/resolve/$rev/$f"
done
echo "$dir"
