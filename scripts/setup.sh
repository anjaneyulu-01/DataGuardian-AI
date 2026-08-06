#!/usr/bin/env bash
# One-time local setup for macOS / Linux.
#   bash scripts/setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# One .env at the repository root configures the backend, the frontend, and
# docker-compose. Create it first so both installs see it.
echo "==> Root: environment file"
cd "$ROOT"
if [ -f .env ]; then
  echo "    .env already exists, leaving it alone"
else
  cp .env.example .env
  echo "    created .env from .env.example"
fi

echo "==> Backend: creating virtual environment (Python 3.12)"
cd "$ROOT/backend"
[ -d .venv ] || python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt

echo "==> Frontend: installing npm dependencies"
cd "$ROOT/frontend"
npm install

echo
echo "Setup complete."
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
