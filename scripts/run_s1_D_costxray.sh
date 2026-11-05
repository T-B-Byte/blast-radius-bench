#!/bin/bash
# local machine half of D held-out v2: cost-xray only, separate tag _v2s1 (merge into __D_v2__cost-xray later)
cd .
M=hf.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf
echo "=== START $(date) D cost-xray on local machine (split from local machine) ===" >> logs/run_26B-A4B_D_heldout_v2_s1_costxray.log
.venv/bin/python bench/agent.py --model $M --setting D --split heldout --repo cost-xray --limit 50 --tag _v2s1 --host http://127.0.0.1:11435 >> logs/run_26B-A4B_D_heldout_v2_s1_costxray.log 2>&1 && echo DONE > logs/s1_D_done
