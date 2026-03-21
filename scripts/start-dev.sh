#!/bin/bash
set -e

echo "MediaForge Development Mode"
echo "==========================="

# Start backend
echo "Starting backend on :8686..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8686 &
BACKEND_PID=$!

# Start frontend dev server
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "Starting frontend dev server on :5173..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

# Trap SIGTERM/SIGINT for clean shutdown
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGTERM SIGINT

echo ""
echo "Backend:  http://localhost:8686"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8686/api/docs"
echo ""

wait
