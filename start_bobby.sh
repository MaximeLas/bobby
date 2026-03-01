#!/bin/bash
# Bobby - Complete System Launcher
# Starts all 3 components in a tmux session with split panes
#
# Usage:
#   ./start_bobby.sh              # Full mode (launches agents)
#   ./start_bobby.sh --test-voice # Test mode (voice only, no agents)

# Always run from the project root (where this script lives)
cd "$(dirname "$0")"

# Check for --test-voice flag
TEST_VOICE_FLAG=""
if [ "$1" == "--test-voice" ]; then
    TEST_VOICE_FLAG="--test-voice"
    echo "🎤 Starting Bobby in VOICE TEST MODE (no agents will be launched)"
else
    echo "🚀 Starting Bobby in FULL MODE"
fi

# Kill existing Bobby session if it exists
tmux kill-session -t bobby 2>/dev/null

echo ""
echo ""
echo "Layout:"
echo "┌─────────────────────────────┬─────────────────────────────┐"
echo "│                             │                             │"
echo "│   Audio Capture             │   Orchestrator              │"
echo "│   (Assembly AI)             │   (Trigger Detection)       │"
echo "│                             │                             │"
echo "├─────────────────────────────┴─────────────────────────────┤"
echo "│                                                           │"
echo "│   Progress Watcher                                        │"
echo "│   (Bobby's Updates)                                       │"
echo "│                                                           │"
echo "└───────────────────────────────────────────────────────────┘"
echo ""
echo "Controls:"
echo "  • Switch panes: Ctrl+b then arrow keys"
echo "  • Stop Bobby: Ctrl+c in each pane, or run: tmux kill-session -t bobby"
echo "  • Detach (keep running): Ctrl+b then d"
echo "  • Reattach later: tmux attach -t bobby"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Resolve absolute path to project root (for tmux panes which start in $HOME)
PROJECT_DIR="$(pwd)"

# Build env var export prefix for tmux panes
# Forward BOBBY_WORKSPACE if set, so tmux panes inherit it
ENV_EXPORT=""
if [ -n "$BOBBY_WORKSPACE" ]; then
    ENV_EXPORT="export BOBBY_WORKSPACE='$BOBBY_WORKSPACE' && "
fi

# Create new tmux session named "bobby" (detached)
tmux new-session -d -s bobby -n "Bobby"

# Split window horizontally (creates right pane)
tmux split-window -h -t bobby

# Split bottom pane vertically (creates bottom pane)
tmux split-window -v -t bobby:0.0

# Adjust pane sizes for better layout
# Make bottom pane (progress watcher) taller
tmux resize-pane -t bobby:0.2 -y 15

# Send commands to each pane (using uv run from project root)
# Pane 0 (top-left): Audio Capture
tmux send-keys -t bobby:0.0 "cd $PROJECT_DIR && ${ENV_EXPORT}echo '🎤 Audio Capture Starting...' && sleep 1 && uv run python3 -m bobby.audio_capture" C-m

# Pane 1 (top-right): Orchestrator
tmux send-keys -t bobby:0.1 "cd $PROJECT_DIR && ${ENV_EXPORT}echo '🤖 Orchestrator Starting...' && sleep 1 && uv run python3 -m bobby.orchestrator $TEST_VOICE_FLAG" C-m

# Pane 2 (bottom): Progress Watcher
tmux send-keys -t bobby:0.2 "cd $PROJECT_DIR && ${ENV_EXPORT}echo '👀 Progress Watcher Starting...' && sleep 1 && uv run python3 -m bobby.progress_watcher" C-m

# Attach to the session
tmux attach-session -t bobby
