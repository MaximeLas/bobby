#!/usr/bin/env bash
#
# Return sandbox/ to its committed blank-canvas state between test and demo
# runs — one command, safe to run twice.
#
#   bash tools/reset_sandbox.sh
#
# `git clean` runs WITHOUT -x on purpose: node_modules/ and dist/ are
# gitignored and cost minutes to rebuild, so they survive every reset. Only
# tracked edits and new untracked files the agent wrote go away.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ Restoring tracked files in sandbox/"
git restore sandbox/

echo "→ Removing untracked files in sandbox/ (keeping node_modules/, dist/)"
git clean -fd sandbox/

echo "→ Removing runtime state files"
rm -f \
    sandbox/meeting_transcript.txt \
    sandbox/agent_progress.txt \
    sandbox/events.jsonl \
    sandbox/bobby_last_speech.txt \
    sandbox/pause_transcription.flag \
    sandbox/speaker_names.txt

echo "→ Freeing port 5173 (leftover dev server)"
lsof -ti:5173 | xargs kill 2>/dev/null || true

echo "sandbox reset — git status --short sandbox/ (empty means clean):"
git status --short sandbox/
