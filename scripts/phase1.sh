# Phase 1 launcher: private Ollama server (port 11435, models in project folder), model downloads,
# dataset build, and smoke test - all in the background with logs in ./logs.
source "$(dirname "$0")/env.sh"
mkdir -p logs models
curl -s "$HOST_URL/api/version" >/dev/null || { nohup ollama serve > logs/ollama.log 2>&1 & sleep 4; }
curl -s "$HOST_URL/api/version"; echo
nohup bash scripts/pull_models.sh > logs/pull.log 2>&1 &
nohup bash scripts/build_data.sh > logs/build.log 2>&1 &
nohup bash scripts/smoke.sh > logs/smoke.log 2>&1 &
sleep 20; tail -3 logs/pull.log logs/build.log
