#!/bin/bash
# Double-click or: open research/RUN_RAG_EVAL.command
# Runs the controlled LLM+RAG evaluation outside Cursor sandbox (needs OpenAI network).
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"
export MPLCONFIGDIR="$PWD/.mplconfig"
mkdir -p "$MPLCONFIGDIR" research/results research/figures
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy SOCKS_PROXY socks_proxy SOCKS5_PROXY socks5_proxy || true

if [[ ! -x .venv-eval/bin/python ]]; then
  echo "Creating .venv-eval..."
  /Users/kushsharma/anaconda3/bin/python3.11 -m venv .venv-eval
  .venv-eval/bin/pip install -q faiss-cpu rank-bm25 numpy pandas scikit-learn matplotlib openai python-dotenv tqdm
fi

echo "Probing OpenAI..."
if ! .venv-eval/bin/python - <<'PY'
from dotenv import load_dotenv
import os
load_dotenv("research/.env")
load_dotenv("backend/.env")
from openai import OpenAI
c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
c.embeddings.create(model="text-embedding-3-small", input=["ok"])
print("OpenAI OK")
PY
then
  echo "ERROR: OpenAI not reachable. Check network and OPENAI_API_KEY in research/.env"
  read -r -p "Press enter to close..."
  exit 1
fi

echo "Running full RAG evaluation (n=100) — this may take 15–40 minutes..."
.venv-eval/bin/python -u research/run_rag_vs_llm_eval.py
echo ""
echo "Done. Results in research/results/ and research/figures/"
echo "See research/results/rq_answer_summary.md for the research question answer."
read -r -p "Press enter to close..."
