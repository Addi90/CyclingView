#!/bin/bash

PID_FILE=".do.pids"

init() {
  echo "Initializing backend environment..."
  python3 -m venv backend/.venv
  ./backend/.venv/bin/pip install -e backend
  
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
  
  echo "Initialization complete."
}

start() {
  echo "Starting backend..."
  # Run uvicorn in the background using the venv's python
  (cd backend && ./.venv/bin/python3 -m uvicorn app.main:app --reload --port 8000 --app-dir backend) &
  echo $! >> $PID_FILE
  
  echo "Starting frontend..."
  (cd frontend && npm run dev) &
  echo $! >> $PID_FILE
  
  echo "Application started. PIDs saved to $PID_FILE"
}

stop() {
  if [ -f "$PID_FILE" ]; then
    echo "Stopping application..."
    while read -r pid; do
      # Kill the process and its children
      pkill -P "$pid" 2>/dev/null
      kill "$pid" 2>/dev/null
    done < "$PID_FILE"
    rm "$PID_FILE"
    echo "Application stopped."
  else
    echo "No running processes found in $PID_FILE."
  fi
}

case "$1" in
  init)
    init
    ;;
  start)
    start
    ;;
  stop)
    stop
    ;;
  *)
    echo "Usage: $0 {init|start|stop}"
    exit 1
    ;;
esac
