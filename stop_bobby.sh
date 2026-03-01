#!/bin/bash
# Stop Bobby - Kill the tmux session cleanly

echo "🛑 Stopping Bobby..."
tmux kill-session -t bobby 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Bobby stopped successfully"
else
    echo "⚠️  Bobby session not found (already stopped?)"
fi
