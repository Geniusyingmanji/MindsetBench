#!/usr/bin/env bash
# Preregistered far20 calibration run (docs/FAR_TRANSFER_PROTOCOL.md §7).
#
#   MINDSETBENCH_API_KEY=... scripts/run_far20_calibration.sh [model] [endpoint] [stage]
#
# stage = target   : target-only only (3 samples x 12 L2-L4 targets = 36 calls)
# stage = paired   : with-source, with-lure, with-both on the same slice (108 calls)
# stage = all      : both stages in sequence (default)
#
# Results land in artifacts/runs/ (git-ignored). The API key is read from the
# environment only; never pass it on the command line or write it into the repo.
set -euo pipefail

MODEL="${1:-gpt-5.6-sol}"
ENDPOINT="${2:-https://matrixllm.alipay.com/v1/chat/completions}"
STAGE="${3:-all}"
DATASET="data/manifests/far20-hard.json"
DB="artifacts/runs/far20-hard-${MODEL}.sqlite"
EXP="far20-hard-${MODEL}-s3-v1"
MB="${MB:-.venv/bin/mb}"

if [[ -z "${MINDSETBENCH_API_KEY:-}" ]]; then
  echo "MINDSETBENCH_API_KEY is not set" >&2
  exit 2
fi
mkdir -p artifacts/runs

run_conditions() {
  "$MB" run \
    --dataset "$DATASET" \
    --database "$DB" \
    --experiment-id "$EXP" \
    --model "$MODEL" \
    --endpoint "$ENDPOINT" \
    --conditions "$@" \
    --samples-per-item 3 \
    --max-output-tokens 4096 \
    --concurrency 4 \
    --request-timeout-seconds 240 >/dev/null
}

if [[ "$STAGE" == "target" || "$STAGE" == "all" ]]; then
  echo "== stage 1: target-only =="
  run_conditions target-only
  "$MB" report --database "$DB" --experiment-id "$EXP" --part-details \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps({k:d[k] for k in ("accuracy","part_accuracy","completion_rate","copy_probe_rate_by_condition","lure_answer_rate_by_condition","by_level","by_schema")}, ensure_ascii=False, indent=2))'
fi

if [[ "$STAGE" == "paired" || "$STAGE" == "all" ]]; then
  echo "== stage 2: with-source / with-lure / with-both =="
  run_conditions with-source with-lure with-both
  "$MB" report --database "$DB" --experiment-id "$EXP" --calibration-gates --min-samples 3 --part-details \
    > "artifacts/runs/${EXP}-report.json"
  python3 - "artifacts/runs/${EXP}-report.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
keys = ("accuracy", "part_accuracy", "completion_rate", "transfer_gain", "with_both_gain",
        "selection_loss", "structural_selectivity", "copy_probe_rate_by_condition",
        "lure_answer_rate_by_condition", "completed_efficiency", "by_level", "by_schema", "calibration")
print(json.dumps({k: d.get(k) for k in keys}, ensure_ascii=False, indent=2))
PY
  echo "full report: artifacts/runs/${EXP}-report.json"
fi
