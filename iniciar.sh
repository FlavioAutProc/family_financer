#!/usr/bin/env bash
# Orçamento Familiar Pro — inicia o sistema (Linux/macOS)
set -e
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "Primeira vez: preparando o sistema (leva alguns minutos)..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip --quiet
  .venv/bin/python -m pip install -r requirements.txt --quiet
fi
echo "Abrindo o Orçamento Familiar Pro no navegador... (Ctrl+C para encerrar)"
exec .venv/bin/python -m streamlit run app.py
