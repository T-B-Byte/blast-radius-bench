# Build dev-split tasks + graphs + baselines (no model needed).
source "$(dirname "$0")/env.sh"
[ -x "$PY" ] || uv venv --quiet --python 3.12 "$P/.venv"
for r in toolz boltons cachetools humanize more-itertools; do
  echo "=== $(date) $r"
  "$PY" bench/prepare.py --only $r && "$PY" bench/graph.py $r && "$PY" bench/label.py $r --n 200 --timeout 60 || echo "BUILD_FAILED $r"
done
"$PY" bench/baselines.py && "$PY" bench/score.py
echo "BUILD_DONE $(date)"
