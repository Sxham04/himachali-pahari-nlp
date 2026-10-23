#!/usr/bin/env bash
# Stage 2 data-size ablation (25/50/75%), joint model first, then the separate ones.
# Runs in WSL2 Ubuntu, because Windows Smart App Control blocks torch's DLLs. From Windows:
#   wsl -d Ubuntu -- bash src/stage2_wsl.sh
# Linux venv in ~/venvs/reg-finetune (uv sync --frozen); NLLB read from the Windows HF cache.
# Resumable: runs with a train_log.json are skipped. Logs in models/<run>.log.
# Under WSL the 8 GB GPU ran full at batch 16 and runs hit random "CUDA error: unknown error"s, so: micro-batch 8 x
# 2 accumulation steps (same effective batch 16 as Stage 1), and up to 3 tries per run, each resuming from the last
# epoch checkpoint. (PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True fails under WSL: "device not ready".)
set -u
cd "$(dirname "$0")/.."
export UV_PROJECT_ENVIRONMENT=$HOME/venvs/reg-finetune UV_LINK_MODE=copy PYTHONIOENCODING=utf-8 \
       HF_HUB_CACHE=/mnt/c/Users/sharm/.cache/huggingface/hub HF_HUB_OFFLINE=1
for langs in "mjl kfs xnr" mjl kfs xnr; do
  for f in 25 50 75; do
    name=$([ "$langs" = "mjl kfs xnr" ] && echo joint || echo "$langs")_f$f
    for try in 1 2 3; do
      [ -f "results/finetune/$name/train_log.json" ] && break
      echo "$(date '+%F %H:%M') start $name (try $try)"
      ~/.local/bin/uv run --frozen python src/finetune.py --langs $langs --frac 0.$f --accum 2 >> "models/$name.log" 2>&1
      rc=$?
      echo "$(date '+%F %H:%M') end $name (exit $rc)"
    done
  done
done
