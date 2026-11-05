# Download official Google Gemma 4 QAT Q4_0 GGUFs from Hugging Face (ungated, Apache-2.0)
# into the project-local Ollama store. Order: smallest useful first.
source "$(dirname "$0")/env.sh"
for m in E4B 26B-A4B 12B 31B; do
  ref="hf.co/google/gemma-4-$m-it-qat-q4_0-gguf"
  echo "=== $(date) pulling $ref"
  if ollama pull "$ref"; then echo "OK $ref"; else echo "PULL_FAILED $ref"; fi
done
ollama list
echo "PULL_DONE $(date)"
