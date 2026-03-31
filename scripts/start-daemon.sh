#!/usr/bin/env bash
#
# start-daemon.sh - Start all Aura development services in daemon mode
#
# This script starts Aura services in the background without keeping
# the terminal connection. Logs are written to separate files.
#
# Must be run from the repo root directory.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Stop existing services ────────────────────────────────────────────────────

echo "Stopping existing services if any..."
pkill -f "langgraph dev" 2>/dev/null || true
pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
sleep 1
pkill -9 nginx 2>/dev/null || true
./scripts/cleanup-containers.sh aura-sandbox 2>/dev/null || true
sleep 1

# ── Banner ────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo " Starting Aura in Daemon Mode"
echo "=========================================="
echo ""

# ── Config check ─────────────────────────────────────────────────────────────

if ! { \
        [ -n "$AURA_CONFIG_PATH" ] && [ -f "$AURA_CONFIG_PATH" ] || \
        [ -f backend/config.yaml ] || \
        [ -f config.yaml ]; \
    }; then
    echo "✗ No Aura config file found."
    echo "  Checked these locations:"
    echo "    - $AURA_CONFIG_PATH (when AURA_CONFIG_PATH is set)"
    echo "    - backend/config.yaml"
    echo "    - ./config.yaml"
    echo ""
    echo "  Run 'make config' from the repo root to generate ./config.yaml, then set required model API keys in .env or your config file."
    exit 1
fi

# ── Auto-upgrade config ──────────────────────────────────────────────────

"$REPO_ROOT/scripts/config-upgrade.sh"

# ── Model config preflight ───────────────────────────────────────────────

MODEL_CHECK_OUTPUT="$(cd backend && PYTHONPATH=. uv run python -c 'from aura.config.app_config import get_app_config; cfg = get_app_config(); print(f"__MODEL__:{cfg.models[0].name}" if cfg.models else "__NO_MODELS__")' 2>&1)"
MODEL_CHECK_STATUS=$?
MODEL_CHECK_LINE="$(printf '%s\n' "$MODEL_CHECK_OUTPUT" | tail -n 1)"

if [ $MODEL_CHECK_STATUS -ne 0 ]; then
    echo "✗ Failed to validate model configuration."
    printf '%s\n' "$MODEL_CHECK_OUTPUT"
    exit 1
fi

if [ "$MODEL_CHECK_LINE" = "__NO_MODELS__" ]; then
    echo "✗ No chat models configured."
    echo "  Add at least one entry under 'models:' in ./config.yaml,"
    echo "  or save a provider from the UI so Aura can inject a custom model."
    echo "  Example: uncomment and fill in the Anthropic or OpenAI model block in ./config.yaml."
    exit 1
fi

if [ "${MODEL_CHECK_LINE#__MODEL__:}" != "$MODEL_CHECK_LINE" ]; then
    echo "✓ Default model configured: ${MODEL_CHECK_LINE#__MODEL__:}"
fi

# ── Cleanup on failure ───────────────────────────────────────────────────────

cleanup_on_failure() {
    echo "Failed to start services, cleaning up..."
    pkill -f "langgraph dev" 2>/dev/null || true
    pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
    sleep 1
    pkill -9 nginx 2>/dev/null || true
    echo "✓ Cleanup complete"
}

trap cleanup_on_failure INT TERM

# ── Start services ────────────────────────────────────────────────────────────

mkdir -p logs

echo "Starting LangGraph server..."
nohup sh -c 'cd backend && NO_COLOR=1 uv run langgraph dev --no-browser --allow-blocking --no-reload > ../logs/langgraph.log 2>&1' &

echo "Starting Gateway API..."
nohup sh -c 'cd backend && PYTHONPATH=. uv run uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001 > ../logs/gateway.log 2>&1' &
./scripts/wait-for-port.sh 8001 30 "Gateway API" || {
    echo "✗ Gateway API failed to start. Last log output:"
    tail -60 logs/gateway.log
    echo ""
    echo "  Hint: Try running 'make config-upgrade' to update your config.yaml with the latest fields."
    cleanup_on_failure
    exit 1
}
echo "✓ Gateway API started on localhost:8001"

echo "Starting Frontend..."
nohup sh -c 'cd frontend && pnpm run dev > ../logs/frontend.log 2>&1' &
./scripts/wait-for-port.sh 3000 120 "Frontend" || {
    echo "✗ Frontend failed to start. Last log output:"
    tail -60 logs/frontend.log
    cleanup_on_failure
    exit 1
}
echo "✓ Frontend started on localhost:3000"

echo "Starting Nginx reverse proxy..."
nohup sh -c 'nginx -g "daemon off;" -c "$1/docker/nginx/nginx.local.conf" -p "$1" > logs/nginx.log 2>&1' _ "$REPO_ROOT" &
./scripts/wait-for-port.sh 2026 10 "Nginx" || {
    echo "✗ Nginx failed to start. Last log output:"
    tail -60 logs/nginx.log
    cleanup_on_failure
    exit 1
}
echo "✓ Nginx started on localhost:2026"

# ── Ready ─────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo " Aura is running in daemon mode!"
echo "=========================================="
echo ""
echo " 🌐 Application: http://localhost:2026"
echo " 📡 API Gateway: http://localhost:2026/api/*"
echo " 🤖 LangGraph: http://localhost:2026/api/langgraph/*"
echo ""
echo " 📋 Logs:"
echo " - LangGraph: logs/langgraph.log"
echo " - Gateway: logs/gateway.log"
echo " - Frontend: logs/frontend.log"
echo " - Nginx: logs/nginx.log"
echo ""
echo " ⏳ LangGraph starts in the background and may still be warming up."
echo " 🛑 Stop daemon: make stop"
echo ""
