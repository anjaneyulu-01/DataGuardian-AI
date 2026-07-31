#!/usr/bin/env bash
# One-time local setup for macOS / Linux.
#   bash scripts/setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend: creating virtual environment (Python 3.12)"
cd "$ROOT/backend"
[ -d .venv ] || python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
[ -f .env ] || cp .env.example .env

echo "==> Frontend: installing npm dependencies"
cd "$ROOT/frontend"
npm install
[ -f .env.local ] || cp .env.example .env.local

echo "==> Root: compose environment file"
cd "$ROOT"
[ -f .env ] || cp .env.example .env

echo
echo "Setup complete."
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
