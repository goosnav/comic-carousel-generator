#!/usr/bin/env bash
# Comic Carousel Generator. Double-click run.command or run ./run.sh to open the GUI.
# Headless: ./run.sh scan1.jpg scan2.jpg [--out DIR]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v uv >/dev/null 2>&1; then
  echo "I need uv to fetch Python and the dependencies once. Install it with:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "then run this again."
  exit 1
fi
export GOOSNAV_CALLER_CWD="$PWD" GOOSNAV_APP_ROOT="$HERE/app" GOOSNAV_HOST="${GOOSNAV_HOST:-127.0.0.1}" GOOSNAV_PORT_PREFERENCE="${GOOSNAV_PORT_PREFERENCE:-0}"
cd "$HERE/app"
exec uv run --locked --managed-python --no-dev python launcher/bootstrap.py "$@"
