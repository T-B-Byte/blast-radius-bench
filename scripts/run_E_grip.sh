#!/bin/bash
cd .
M=hf.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf
R=grip
echo "=== START $(date) E $R local machine (retry-on-500) ===" >> logs/run_26B-A4B_E_heldout_v2_$R.log
.venv/bin/python bench/agent.py --model $M --setting E --split heldout --repo $R --limit 50 --tag _v2 --host http://127.0.0.1:11435 >> logs/run_26B-A4B_E_heldout_v2_$R.log 2>&1 && echo DONE > logs/s1_E_${R}_done
