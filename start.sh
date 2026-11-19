#!/usr/bin/env sh
# Start de demo: maakt een eigen Python-omgeving, de verzonnen schijf en de webinterface.
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
[ -d demo-t-schijf ] || .venv/bin/python maak_demodata.py
echo "Open http://${HOST:-127.0.0.1}:${PORT:-8010}"
exec .venv/bin/uvicorn tschijf.app:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8010}"
