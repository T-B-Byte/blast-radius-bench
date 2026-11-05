# Build held-out-split tasks (repos first committed after Gemma 4's Mar 31, 2026 release).
source "$(dirname "$0")/env.sh"
until grep -q BUILD_DONE logs/build.log; do sleep 30; done
for r in browser-harness cost-xray grip SkillOpt; do
  echo "=== $(date) $r"
  "$PY" bench/prepare.py --only $r && "$PY" bench/graph.py $r && "$PY" bench/label.py $r --n 150 --timeout 60 || echo "BUILD_FAILED $r"
done
"$PY" bench/baselines.py && "$PY" bench/score.py
echo "HELDOUT_DONE $(date)"
