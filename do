#!/usr/bin/env bash
# Convenience entry point for common development tasks.
set -euo pipefail
cd "$(dirname "$0")"

PY=backend/.venv/bin/python
RUNTIME_DIR=.do
mkdir -p "$RUNTIME_DIR"

_pid_alive() { # $1 = service name (backend|frontend)
  [ -f "$RUNTIME_DIR/$1.pid" ] && kill -0 "$(cat "$RUNTIME_DIR/$1.pid")" 2>/dev/null
}

start_one() { # $1 = backend|frontend — the port is the source of truth
  if [ "$1" = backend ]; then port=8080; else port=5173; fi
  holder=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
  if [ -n "$holder" ]; then
    if _pid_alive "$1" && [ "$(cat "$RUNTIME_DIR/$1.pid")" = "$holder" ]; then
      echo "$1: already running (pid $holder)"
      return 0
    fi
    echo "$1: port $port in use by pid $holder (not ours) — free it first" >&2
    return 1
  fi
  if [ "$1" = backend ]; then
    nohup "$PY" -m uvicorn app.main:app --port 8080 >>"$RUNTIME_DIR/backend.log" 2>&1 &
  else
    [ -d frontend/node_modules ] || {
      echo "frontend: missing node_modules — run: npm install --prefix frontend" >&2
      return 1
    }
    # one pid (exec), and vite roots at cwd, so cd first, expose dev server on all interfaces, and redirect logs to a file
    nohup bash -c 'cd frontend && exec node node_modules/.bin/vite -- --host 0.0.0.0' >>"$RUNTIME_DIR/frontend.log" 2>&1 &
  fi
  pid=$!
  echo "$pid" > "$RUNTIME_DIR/$1.pid"
  sleep 1 # let a bind failure surface before we call it running
  if kill -0 "$pid" 2>/dev/null; then
    echo "$1: started (pid $pid, log: $RUNTIME_DIR/$1.log)"
  else
    holder=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
    if [ -n "$holder" ]; then
      echo "$1: failed to start — port $port taken by pid $holder" >&2
    else
      echo "$1: failed to start — check $RUNTIME_DIR/$1.log" >&2
    fi
    rm -f "$RUNTIME_DIR/$1.pid"
    return 1
  fi
}

stop_one() { # $1 = backend|frontend
  if _pid_alive "$1"; then
    pid=$(cat "$RUNTIME_DIR/$1.pid")
    pkill -TERM -P "$pid" 2>/dev/null || true # kill children too
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do # wait for graceful exit (uvicorn drains first)
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
    done
    echo "$1: stopped (pid $pid)"
  else
    echo "$1: not running"
  fi
  rm -f "$RUNTIME_DIR/$1.pid"
}

do_start() {
  case "${1:-all}" in
    all) start_one backend; start_one frontend ;;
    backend|frontend) start_one "$1" ;;
    *) echo "usage: do start [all|backend|frontend]" >&2; exit 1 ;;
  esac
}

do_stop() {
  case "${1:-all}" in
    all) stop_one backend; stop_one frontend ;;
    backend|frontend) stop_one "$1" ;;
    *) echo "usage: do stop [all|backend|frontend]" >&2; exit 1 ;;
  esac
}

cmd="${1:-help}"
case "$cmd" in
  test)
    "$PY" -m pytest -q
    ;;
  ingest)
    "$PY" -m app.ingest "${2:?usage: do ingest <strava_export_dir>}"
    ;;
  serve)
    exec "$PY" -m uvicorn app.main:app --port "${2:-8080}"
    ;;
  start)
    do_start "${2:-all}"
    ;;
  stop)
    do_stop "${2:-all}"
    ;;
  docker)
    docker compose up --build
    ;;
  help)
    grep -E '^  [a-z]+\)' "$0" | sed 's/^  \([a-z]*\).*/\1/' | paste -sd ' ' -
    echo "usage: do <command> [args]   (do help for commands: test, ingest, serve, start, stop, docker, help)"
    ;;
  *)
    echo "unknown command: $cmd (try: do help)" >&2
    exit 1
    ;;
esac