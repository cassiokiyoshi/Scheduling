#!/bin/zsh

set -u

SCRIPT_DIR="${0:A:h}"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  osascript -e 'display dialog "DEN Scheduler is not installed on this computer yet. Open Terminal in the app folder and run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" buttons {"OK"} default button "OK" with icon caution'
  exit 1
fi

cd "$SCRIPT_DIR" || exit 1
"$VENV_PYTHON" -m streamlit run app.py --server.headless false

