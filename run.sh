#!/usr/bin/env bash
set -e

# Multi-Platform Social Video Publisher Startup Script
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================="
echo " Starting Multi-Platform Social Video Publisher"
echo "=========================================================="

# 1. Setup Python Virtual Environment
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "[✓] Python virtualenv found at .venv"
else
    echo "[+] Creating Python virtual environment..."
    if command -v /opt/homebrew/bin/python3.11 >/dev/null 2>&1; then
        PYTHON_BIN="/opt/homebrew/bin/python3.11"
    elif command -v python3.11 >/dev/null 2>&1; then
        PYTHON_BIN="python3.11"
    else
        PYTHON_BIN="python3"
    fi
    echo "[+] Using $PYTHON_BIN"
    "$PYTHON_BIN" -m venv "$PROJECT_ROOT/.venv"
fi

source "$PROJECT_ROOT/.venv/bin/activate"

# 2. Check and Install Backend Dependencies
echo "[+] Checking backend dependencies..."
pip install -q -r "$PROJECT_ROOT/backend/requirements.txt"

# 3. Ensure Playwright Chromium is installed
echo "[+] Checking Playwright Chromium browser..."
python -m playwright install chromium

# 4. Check Frontend Dependencies
if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "[✓] Frontend dependencies already installed"
else
    echo "[+] Installing frontend dependencies..."
    (cd "$PROJECT_ROOT/frontend" && npm install)
fi

# 5. Trap cleanup to kill background processes on exit
cleanup() {
    echo ""
    echo "[!] Shutting down servers..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 6. Launch Backend Server
echo "[+] Launching FastAPI backend on http://localhost:8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend &
BACKEND_PID=$!

# 7. Launch Frontend Server
echo "[+] Launching React Vite frontend on http://localhost:5173..."
(cd "$PROJECT_ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

# 8. Open Browser Window
(
    sleep 2
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:5173"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:5173"
    fi
) &

echo "=========================================================="
echo " Application running at: http://localhost:5173"
echo " API Docs available at:  http://localhost:8000/docs"
echo " Press Ctrl+C to terminate both servers."
echo "=========================================================="

# Wait for both child processes
wait $BACKEND_PID $FRONTEND_PID
