#!/usr/bin/env bash
set -euo pipefail

# GoStayPro local run helper
# - Creates a virtual environment in .venv if missing
# - Installs dependencies from requirements.txt
# - Creates a local .env from .env.example if missing
# - Runs the FastAPI app with Uvicorn in reload mode

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN=${PYTHON:-python3}
PORT=${PORT:-8000}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN not found. Please install Python 3.10+ and/or set PYTHON=<path>." >&2
  exit 1
fi

# Create venv if needed
if [ ! -d .venv ]; then
  echo "Creating virtual environment (.venv)..."
  "$PYTHON_BIN" -m venv .venv
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip and install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# Prepare environment file
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
  else
    echo "Warning: .env.example not found. Proceeding without creating .env." >&2
  fi
fi

export DEBUG=true

# Inform about database selection
if [ -z "${DATABASE_URL:-}" ]; then
  echo "Using default SQLite database (staycal.db). Set DATABASE_URL to use PostgreSQL."
else
  echo "Using DATABASE_URL from environment."
fi

echo "Starting GoStayPro locally at http://127.0.0.1:${PORT} (reload enabled)"
exec uvicorn app.main:app --host 127.0.0.1 --port "${PORT}" --reload
