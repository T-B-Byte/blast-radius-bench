# Smoke test: 5 toolz tasks x settings A/B/C with each model that has finished downloading.
source "$(dirname "$0")/env.sh"
until [ -f data/toolz/tasks.jsonl ] && [ -f data/toolz/graph.json ]; do sleep 20; done
for m in E4B 26B-A4B; do
  ref="hf.co/google/gemma-4-$m-it-qat-q4_0-gguf"
  until ollama list | grep -q "gemma-4-$m-it-qat"; do sleep 30; done
  for s in A B C; do
    "$PY" bench/agent.py --model "$ref" --setting $s --repo toolz --limit 5 --host "$HOST_URL" --tag _smoke || echo "SMOKE_FAILED $m $s"
  done
done
"$PY" bench/score.py
echo "SMOKE_DONE $(date)"
