#!/bin/bash

# Demo script for Bobby Progress Watcher
# Shows what the watcher does in action.
#
# Usage: ./tests/demo_progress_watcher.sh
#        (run from the project root)

PROGRESS_FILE="sandbox/agent_progress.txt"

echo "Bobby Progress Watcher - Live Demo"
echo "===================================="
echo ""
echo "This demo will:"
echo "  1. Start the progress watcher"
echo "  2. Simulate Bobby working on a task"
echo "  3. Show real-time updates in the terminal"
echo "  4. Send macOS notifications"
echo ""
echo "Press Enter to start the demo..."
read

# Ensure sandbox directory exists
mkdir -p sandbox

# Clear progress file
echo "Setting up demo..."
> "$PROGRESS_FILE"

# Start progress watcher in background
echo "Starting progress watcher..."
uv run python3 -m bobby.progress_watcher &
WATCHER_PID=$!

# Give it time to start
sleep 2

echo ""
echo "Progress watcher is running!"
echo "   Watch the terminal output above for colored updates"
echo "   Watch your screen for macOS notifications"
echo ""
echo "Simulating Bobby building a feature..."
echo ""

# Simulate Bobby working
sleep 1
echo "   -> Reading transcript..."
echo "PROGRESS: -> Reading meeting transcript..." >> "$PROGRESS_FILE"
sleep 2

echo "   Done: Found task"
echo "PROGRESS:   Done: Identified task: Build pricing section" >> "$PROGRESS_FILE"
sleep 2

echo "   -> Creating components..."
echo "PROGRESS: -> Creating PricingTable component..." >> "$PROGRESS_FILE"
sleep 2

echo "   Done: Component created"
echo "PROGRESS:   Done: Component created successfully" >> "$PROGRESS_FILE"
sleep 2

echo "   ? Asking question..."
echo "QUESTION: Should pricing default to monthly or annual?" >> "$PROGRESS_FILE"
sleep 3

echo "   -> Continuing work..."
echo "PROGRESS: -> Implementing monthly pricing as default..." >> "$PROGRESS_FILE"
sleep 2

echo "   Done: Implementation complete"
echo "PROGRESS:   Done: Monthly pricing implemented" >> "$PROGRESS_FILE"
sleep 2

echo "   Task complete!"
echo "COMPLETE: Pricing section deployed to localhost:5173" >> "$PROGRESS_FILE"
sleep 3

echo ""
echo "===================================="
echo "DEMO COMPLETE!"
echo ""
echo "You should have seen:"
echo "  - Colored terminal output above (from the watcher)"
echo "  - Multiple macOS notifications"
echo "  - Different styles for each update type"
echo "  - Timestamps on each update"
echo ""
echo "Stopping progress watcher..."
kill $WATCHER_PID 2>/dev/null

echo ""
echo "Demo finished!"
echo ""
echo "To run the watcher manually:"
echo "  Terminal 1: uv run python3 -m bobby.progress_watcher"
echo "  Terminal 2: uv run python3 tests/test_progress_watcher.py"
echo ""

# Cleanup
echo "Clean up test files? (y/n)"
read -r cleanup
if [ "$cleanup" = "y" ]; then
    rm -f "$PROGRESS_FILE"
    echo "Cleaned up."
fi
