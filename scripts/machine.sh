#!/bin/sh
# Print the hardware of this Linux machine as a Markdown table, then the measured speed of each
# evaluated model. Prints no serial number, host name, address or user path.
set -eu
cd "$(dirname "$0")/.."

dmi() { cat "/sys/class/dmi/id/$1" 2>/dev/null || echo "?"; }
cpuinfo() { grep -m1 "^$1" /proc/cpuinfo | cut -d: -f2- | sed 's/^ *//'; }

computer="$(dmi sys_vendor) $(dmi product_version) (type $(dmi product_name | cut -c1-4))"
flags=$(cpuinfo flags | tr ' ' '\n' | grep -x -E 'avx2|fma|avx512f' | sort | paste -sd ' ' -)
cpu="$(cpuinfo 'model name'), $(cpuinfo 'cpu cores') cores, $(nproc --all) threads, $flags"
ram=$(awk '/^MemTotal/ {printf "%.1f GiB", $2 / 1048576}' /proc/meminfo)
disk=$(lsblk -d -n -e 7 -o MODEL,SIZE 2>/dev/null | sed 's/  */ /g' | paste -sd ';' - | sed 's/;/; /g')
gpu=$(lspci 2>/dev/null | grep -E 'VGA|3D' | cut -d: -f3- | sed 's/^ *//' | paste -sd ';' - | sed 's/;/; /g')
if [ -r /proc/driver/nvidia/version ]; then
  gpu="$gpu; NVIDIA driver $(awk 'NR == 1 {for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+\.[0-9]+\.[0-9]+$/) print $i}' /proc/driver/nvidia/version)"
fi
os=$(. /etc/os-release && echo "$PRETTY_NAME")
ollama=$(curl -s --max-time 2 "${OLLAMA_URL:-http://127.0.0.1:11434}/api/version" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')

cat <<EOF
| Part | Value |
|---|---|
| Computer | $computer |
| CPU | $cpu |
| RAM | $ram |
| Disk | $disk |
| GPU | $gpu |
| Operating system | $os, kernel $(uname -r), init $(ps -p 1 -o comm=) |
| Ollama | ${ollama:-not running} |
EOF

if [ -f eval/results/summary.json ]; then
  echo
  python3 - <<'EOF'
import json
rows = [r for r in json.load(open("eval/results/summary.json")) if r.get("tok_per_sec")]
print("| Model | Tokens per second | Seconds per text |\n|---|---|---|")
for r in rows:
    print(f"| {r['model']} | {r['tok_per_sec']} | {r['sec_per_text']} |")
EOF
fi
