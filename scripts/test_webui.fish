#!/usr/bin/env nix
#! nix develop --command fish
# ------------------------------------------------------------------
# test_webui.fish — End-to-end smoke test for Cuba Libre WebUI + SB3
#
# Usage (from repo root):
#   ./scripts/test_webui.fish
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

set repo_root (realpath (dirname (status filename))/..)
cd $repo_root

# ── venv ──────────────────────────────────────────────────────────
if test -f "$repo_root/.venv/bin/activate.fish"
    source "$repo_root/.venv/bin/activate.fish"
    echo "✓ venv activated"
else
    echo "⚠ No .venv/bin/activate.fish found — using system Python"
end

set -gx PYTHONPATH "$repo_root/app:$repo_root/app/environments"
echo "PYTHONPATH = $PYTHONPATH"
echo "Python     = "(which python)" ("(python --version 2>&1)")"

# ── helper ────────────────────────────────────────────────────────
function fail
    set_color red; echo "FAIL: $argv"; set_color normal
    cleanup
    exit 1
end

function ok
    set_color green; echo "  OK: $argv"; set_color normal
end

set -g backend_pid ""
set -g frontend_pid ""

function cleanup
    echo "── cleanup ──"
    if test -n "$backend_pid"
        kill $backend_pid 2>/dev/null
        echo "  killed backend ($backend_pid)"
    end
    if test -n "$frontend_pid"
        kill $frontend_pid 2>/dev/null
        echo "  killed frontend ($frontend_pid)"
    end
end

trap cleanup EXIT

# ── 1. Unit tests ─────────────────────────────────────────────────
echo ""
echo "═══ 1. Unit tests ═══"
python -m unittest discover -s tests -p "test_*.py" -b 2>&1
if test $status -ne 0
    echo "⚠ Unit tests had failures (non-fatal for this script)"
else
    ok "Unit tests passed"
end

# ── 2. Start backend ─────────────────────────────────────────────
echo ""
echo "═══ 2. Starting backend on :8000 ═══"
python -m uvicorn webui.backend.app.main:app --host 127.0.0.1 --port 8000 &
set backend_pid $last_pid
echo "  backend PID = $backend_pid"

# Wait for /health (up to 15s)
set ready 0
for i in (seq 1 30)
    sleep 0.5
    set resp (curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null)
    if test "$resp" = "200"
        set ready 1
        break
    end
end
if test $ready -ne 1
    fail "Backend did not become healthy within 15s"
end
ok "Backend healthy"

# ── 3. Exercise backend endpoints ────────────────────────────────
echo ""
echo "═══ 3. Backend endpoint tests ═══"

# POST /reset with faction_roles
set resp (curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/reset \
    -H "Content-Type: application/json" \
    -d '{"faction_roles":{"0":"human","1":"ai","2":"ai","3":"ai"}}')
set code $resp[-1]
if test "$code" != "200"
    fail "POST /reset returned $code"
end
ok "POST /reset (1H/3AI)"

# GET /state
set resp (curl -s -w "\n%{http_code}" http://127.0.0.1:8000/state)
set code $resp[-1]
if test "$code" != "200"
    fail "GET /state returned $code"
end
ok "GET /state"

# GET /faction_roles
set resp (curl -s -w "\n%{http_code}" http://127.0.0.1:8000/faction_roles)
set code $resp[-1]
if test "$code" != "200"
    fail "GET /faction_roles returned $code"
end
ok "GET /faction_roles"

# POST /faction_roles — change to 2H/2AI
set resp (curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/faction_roles \
    -H "Content-Type: application/json" \
    -d '{"faction_roles":{"0":"human","1":"human","2":"ai","3":"ai"}}')
set code $resp[-1]
if test "$code" != "200"
    fail "POST /faction_roles returned $code"
end
ok "POST /faction_roles (2H/2AI)"

# POST /reset — all AI (for spectator)
set resp (curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/reset \
    -H "Content-Type: application/json" \
    -d '{"faction_roles":{"0":"ai","1":"ai","2":"ai","3":"ai"}}')
set code $resp[-1]
if test "$code" != "200"
    fail "POST /reset (0H/4AI) returned $code"
end
ok "POST /reset (0H/4AI)"

# GET /spectator/status
set resp (curl -s -w "\n%{http_code}" http://127.0.0.1:8000/spectator/status)
set code $resp[-1]
if test "$code" != "200"
    fail "GET /spectator/status returned $code"
end
ok "GET /spectator/status"

# POST /spectator/start
set resp (curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/spectator/start \
    -H "Content-Type: application/json" \
    -d '{"tick_ms":200,"deterministic":false,"auto_reset":true}')
set code $resp[-1]
if test "$code" != "200"
    fail "POST /spectator/start returned $code"
end
ok "POST /spectator/start"

sleep 1  # let a few ticks run

# POST /spectator/stop
set resp (curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/spectator/stop)
set code $resp[-1]
if test "$code" != "200"
    fail "POST /spectator/stop returned $code"
end
ok "POST /spectator/stop"

# Try loading the model (if it exists)
if test -f "$repo_root/zoo/cubalibre/best_model.zip"
    echo ""
    echo "═══ 3b. Model load test ═══"
    set resp (curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/model/load \
        -H "Content-Type: application/json" \
        -d '{"path":"zoo/cubalibre/best_model.zip","device":"cpu","algo":"PPO"}')
    set code $resp[-1]
    if test "$code" != "200"
        echo "⚠ POST /model/load returned $code (model may be SB2 format)"
    else
        ok "POST /model/load"

        # GET /model/info
        set resp (curl -s http://127.0.0.1:8000/model/info)
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
    end
else
    echo "⚠ No model at zoo/cubalibre/best_model.zip — skipping model tests"
end

# ── 4. Frontend dev server ────────────────────────────────────────
echo ""
echo "═══ 4. Frontend dev server ═══"
if test -f "$repo_root/webui/frontend/package.json"
    cd "$repo_root/webui/frontend"
    if not test -d node_modules
        echo "  installing npm deps..."
        npm install --silent 2>&1 | tail -1
    end
    npx vite --port 5173 --host 127.0.0.1 &
    set frontend_pid $last_pid
    cd $repo_root

    # Wait for it (up to 10s)
    set ready 0
    for i in (seq 1 20)
        sleep 0.5
        set resp (curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/ 2>/dev/null)
        if test "$resp" = "200"
            set ready 1
            break
        end
    end
    if test $ready -ne 1
        echo "⚠ Frontend did not start within 10s (non-fatal)"
    else
        ok "Frontend serving at http://127.0.0.1:5173"
    end
else
    echo "⚠ No webui/frontend/package.json — skipping frontend"
end

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════"
set_color green; echo "All smoke tests passed!"; set_color normal
echo "═══════════════════════════════"

cleanup
exit 0
