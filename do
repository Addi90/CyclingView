#!/usr/bin/env bash
# Convenience entry point for common development tasks.
set -euo pipefail
cd "$(dirname "$0")"

PY=backend/.venv/bin/python

cmd="${1:-help}"
case "$cmd" in
  test)
    "$PY" -m pytest -q
    ;;
  ingest)
    "$PY" -m app.ingest "${2:?usage: do ingest <strava_export_dir>}"
    ;;
  serve)
    exec "$PY" -m uvicorn app.main:app --port "${2:-8000}"
    ;;
  docker)
    docker compose up --build
    ;;
  help)
    grep -E '^  [a-z]+\)' "$0" | sed 's/^  \([a-z]*\).*/\1/' | paste -sd ' ' -
    echo "usage: do <command> [args]   (do help for commands: test, ingest, serve, docker, help)"
    ;;
  *)
    echo "unknown command: $cmd (try: do help)" >&2
    exit 1
    ;;
esac