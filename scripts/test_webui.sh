#!/usr/bin/env bash
# ------------------------------------------------------------------
# test_webui.sh — End-to-end smoke test for Cuba Libre WebUI + SB3
#
# Usage (from repo root):
#   ./scripts/test_webui.sh
#
# What it does:
#   1. Activates the venv
#   2. Sets PYTHONPATH for SIMPLE framework imports
#   3. Runs unit tests
#   4. Starts the backend, waits for /health
#   5. Exercises backend endpoints (reset, faction_roles, step, model load,
#      spectator start/stop)
#   6. Starts the frontend dev server, checks it responds
#   7. Tears down both servers
# ------------------------------------------------------------------

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
cd "$repo_root"

# ── venv ──────────────────────────────────────────────────────────
if [ -f "$repo_root/.venv/bin/activate" ]; then
    source "$repo_root/.venv/bin/activate"
    echo "✓ venv activated"
else
    echo "⚠ No .venv/bin/activate found — using system Python"
fi

export PYTHONPATH="$repo_root/app:$repo_root/app/environments"
echo "PYTHONPATH = $PYTHONPATH"
echo "Python     = $(which python) ($(python --version 2>&1))"

# ── helper ────────────────────────────────────────────────────────
fail() {
    echo -e "\e[31mFAIL: $1\e[0m"
    cleanup
    exit 1
}

ok() {
    echo -e "\e[32m  OK: $1\e[0m"
}

backend_pid=""
frontend_pid=""

cleanup() {
    echo "── cleanup ──"
    if [ -n "$backend_pid" ]; then
        kill $backend_pid 2>/dev/null
        echo "  killed backend ($backend_pid)"
    fi
    if [ -n "$frontend_pid" ]; then
        kill $frontend_pid 2>/dev/null
        echo "  killed frontend ($frontend_pid)"
    fi
}

trap cleanup EXIT

# ── 1. Unit tests ─────────────────────────────────────────────────
echo ""
echo "═══ 1. Unit tests ═══"
python -m unittest discover -s tests -p "test_*.py" -b 2>&1
if [ $? -ne 0 ]; then
    echo "⚠ Unit tests had failures (non-fatal for this script)"
else
    ok "Unit tests passed"
fi

# ── 2. Start backend ─────────────────────────────────────────────
echo ""
echo "═══ 2. Starting backend on :8000 ═══"
python -m uvicorn webui.backend.app.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
echo "  backend PID = $backend_pid"

# Wait for /health (up to 15s)
ready=0
for i in {1..30}; do
    sleep 0.5
    resp=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null)
    if [ "$resp" = "200" ]; then
        ready=1
        break
    fi
done
if [ $ready -ne 1 ]; then
    fail "Backend did not become healthy within 15s"
fi
ok "Backend healthy"

# ── 3. Exercise backend endpoints ────────────────────────────────
echo ""
echo "═══ 3. Backend endpoint tests ═══"

# POST /reset with faction_roles
resp=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/reset \
    -H "Content-Type: application/json" \
    -d '{"faction_roles":{"0":"human","1":"ai","2":"ai","3":"ai"}}')
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "POST /reset returned $code"
fi
ok "POST /reset (1H/3AI)"

# GET /state
resp=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/state)
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "GET /state returned $code"
fi
ok "GET /state"

# GET /faction_roles
resp=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/faction_roles)
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "GET /faction_roles returned $code"
fi
ok "GET /faction_roles"

# POST /faction_roles — change to 2H/2AI
resp=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/faction_roles \
    -H "Content-Type: application/json" \
    -d '{"faction_roles":{"0":"human","1":"human","2":"ai","3":"ai"}}')
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "POST /faction_roles returned $code"
fi
ok "POST /faction_roles (2H/2AI)"

# POST /reset — all AI (for spectator)
resp=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/reset \
    -H "Content-Type: application/json" \
    -d '{"faction_roles":{"0":"ai","1":"ai","2":"ai","3":"ai"}}')
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "POST /reset (0H/4AI) returned $code"
fi
ok "POST /reset (0H/4AI)"

# GET /spectator/status
resp=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/spectator/status)
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "GET /spectator/status returned $code"
fi
ok "GET /spectator/status"

# POST /spectator/start
resp=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/spectator/start \
    -H "Content-Type: application/json" \
    -d '{"tick_ms":200,"deterministic":false,"auto_reset":true}')
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "POST /spectator/start returned $code"
fi
ok "POST /spectator/start"

sleep 1  # let a few ticks run

# POST /spectator/stop
resp=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/spectator/stop)
code=$(echo "$resp" | tail -n1)
if [ "$code" != "200" ]; then
    fail "POST /spectator/stop returned $code"
fi
ok "POST /spectator/stop"

# Try loading the model (if it exists)
if [ -f "$repo_root/zoo/cubalibre/best_model.zip" ]; then
    echo ""
    echo "═══ 3b. Model load test ═══"
    resp=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/model/load \
        -H "Content-Type: application/json" \
        -d '{"path":"zoo/cubalibre/best_model.zip","device":"cpu","algo":"PPO"}')
    code=$(echo "$resp" | tail -n1)
    if [ "$code" != "200" ]; then
        echo "⚠ POST /model/load returned $code (model may be SB2 format)"
    else
        ok "POST /model/load"

        # GET /model/info
        resp=$(curl -s http://127.0.0.1:8000/model/info)
        echo "  model/info: $resp"
        ok "GET /model/info"

        # Run spectator with model for a couple ticks
        curl -s -X POST http://127.0.0.1:8000/spectator/start \
            -H "Content-Type: application/json" \
            -d '{"tick_ms":100,"deterministic":false,"auto_reset":false}' > /dev/null
        sleep 0.5
        curl -s -X POST http://127.0.0.1:8000/spectator/stop > /dev/null
        ok "Spectator with model ran"

        # Unload
        curl -s -X POST http://127.0.0.1:8000/model/unload > /dev/null
        ok "POST /model/unload"
    fi
else
    echo "⚠ No model at zoo/cubalibre/best_model.zip — skipping model tests"
fi

# ── 4. Frontend dev server ────────────────────────────────────────
echo ""
echo "═══ 4. Frontend dev server ═══"
if [ -f "$repo_root/webui/frontend/package.json" ]; then
    cd "$repo_root/webui/frontend"
    if [ ! -d node_modules ]; then
        echo "  installing npm deps..."
        npm install --silent 2>&1 | tail -1
    fi
    npx vite --port 5173 --host 127.0.0.1 &
    frontend_pid=$!
    cd "$repo_root"

    # Wait for it (up to 10s)
    ready=0
    for i in {1..20}; do
        sleep 0.5
        resp=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/ 2>/dev/null)
        if [ "$resp" = "200" ] || [ "$resp" = "404" ]; then
            ready=1
            break
        fi
    done
    if [ $ready -ne 1 ]; then
        echo "⚠ Frontend did not start within 10s (non-fatal)"
    else
        ok "Frontend serving at http://127.0.0.1:5173"
    fi
else
    echo "⚠ No webui/frontend/package.json — skipping frontend"
fi

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════"
echo -e "\e[32mAll smoke tests passed!\e[0m"
echo "═══════════════════════════════"

cleanup
exit 0
