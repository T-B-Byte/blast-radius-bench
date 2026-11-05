# Full evaluation: held-out split x 4 Gemma 4 sizes x settings A/B/C (3 settings in parallel per model),
# plus a 40-task-per-repo dev subsample (settings A and C) for the contamination check. Resumable.
source "$(dirname "$0")/env.sh"
until grep -q HELDOUT_DONE logs/heldout.log; do sleep 60; done
for m in E4B 26B-A4B 12B 31B; do
  ref="hf.co/google/gemma-4-$m-it-qat-q4_0-gguf"
  until ollama list | grep -q "gemma-4-$m-it-qat"; do sleep 60; done
  echo "=== $(date) $m heldout"
  for s in A B C; do "$PY" bench/agent.py --model "$ref" --setting $s --split heldout --host "$HOST_URL" > logs/run_${m}_${s}_heldout.log 2>&1 & done
  wait
  echo "=== $(date) $m dev subsample"
  for s in A C; do "$PY" bench/agent.py --model "$ref" --setting $s --split dev --limit 40 --host "$HOST_URL" --tag _devsub > logs/run_${m}_${s}_dev.log 2>&1 & done
  wait
  "$PY" bench/score.py --split heldout > logs/scores_heldout.txt
done
echo "FULL_DONE $(date)"
