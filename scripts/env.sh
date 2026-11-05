# Keep everything (Python, caches, models) inside the project folder.
export P="$(pwd)"
export UV_CACHE_DIR="$P/.uv-cache" UV_PYTHON_INSTALL_DIR="$P/.uv-python"
export OLLAMA_MODELS="$P/models" OLLAMA_HOST="127.0.0.1:11435"
export OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_NUM_PARALLEL=4 OLLAMA_KEEP_ALIVE=30m
export HOST_URL="http://127.0.0.1:11435"
export PY="$P/.venv/bin/python"
cd "$P"
