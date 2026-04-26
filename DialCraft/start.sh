#!/bin/bash
# ============================================
#   DialCraft - AI Voice Agent Launcher
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ============================================"
echo "       DialCraft - AI Voice Agent Launcher"
echo "  ============================================"
echo ""

# ── Step 1: Start the AI Server ──────────────────────
echo "[1/3] Starting AI Server..."
conda run -n shrishtiai python main.py &
SERVER_PID=$!
echo "       Server PID: $SERVER_PID"
echo "       Waiting 15 seconds for models to load..."
sleep 15

# ── Step 2: Start ngrok tunnel ───────────────────────
echo "[2/3] Starting ngrok tunnel..."
ngrok http 8000 &
NGROK_PID=$!
echo "       ngrok PID: $NGROK_PID"
echo "       Waiting 5 seconds for tunnel..."
sleep 5

# ── Step 3: Place the call ───────────────────────────
echo "[3/3] Placing call to your phone..."
echo ""
conda run -n shrishtiai python call_me.py

echo ""
echo "  ============================================"
echo "   Your phone should be ringing! Pick up!"
echo "  ============================================"
echo ""
echo "  Press Ctrl+C to shut everything down."

# ── Cleanup on exit ──────────────────────────────────
cleanup() {
    echo ""
    echo "  Shutting down..."
    kill $SERVER_PID 2>/dev/null
    kill $NGROK_PID 2>/dev/null
    echo "  Done."
    exit 0
}
trap cleanup SIGINT SIGTERM

# Keep alive until user hits Ctrl+C
wait
