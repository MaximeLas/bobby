#!/usr/bin/env python3
"""
Manual test: the transcript → trigger → agent-launch → build loop, without a
microphone.

Appends a realistic meeting snippet (ending in the trigger phrase) to the real
transcript file, detects the trigger with the production functions, and
launches the REAL Claude Code agent into the workspace — exactly what the
orchestrator/Discord watcher do when the trigger is spoken. The audio→AAI half
of the pipeline is covered separately by test_streaming_model.py.

COSTS REAL AGENT CREDITS and modifies the workspace (default: ./sandbox).
Run from your own terminal — the nested `claude` CLI authenticates with your
stored login, which sandboxed/child environments may not have access to.

Run:  uv run python3 tests/manual/test_agent_loop.py
      uv run python3 tests/manual/test_agent_loop.py "add a footer with a © line"
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bobby.config import TRANSCRIPT_FILE, PROGRESS_FILE, WORKSPACE_DIR
from bobby.agent_runner import detect_trigger, get_recent_context, launch_agent

DEFAULT_TASK = (
    "A new page at slash night, dark starry background, with a headline that "
    "says 'Built by Bobby at 4am' and a line 'while Max was asleep'. Add a "
    "link back to the home page, and a small 'Night Shift' link on the home "
    "page so it is easy to find."
)


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
    ts = lambda: datetime.now().strftime("%H:%M:%S")

    # 1. Append a meeting snippet ending in the trigger, formatted exactly
    #    as audio_capture.write_transcript would write it.
    snippet = [
        "=== New Recording Session (manual agent-loop test) ===",
        "Okay, next thing for the sandbox app.",
        task,
        "Hey Bobby, please build this.",
    ]
    with open(TRANSCRIPT_FILE, "a") as f:
        for line in snippet:
            f.write(f"[{ts()}] {line}\n")
    print(f"appended {len(snippet)} lines to {TRANSCRIPT_FILE}")

    # 2. Detect the trigger on the new content, as the watchers do.
    trigger = detect_trigger("\n".join(snippet))
    print(f"detect_trigger -> {trigger!r}")
    assert trigger == "launch", f"expected 'launch', got {trigger!r}"

    # 3. Build context and launch the real agent (blocking; takes minutes).
    context = get_recent_context(TRANSCRIPT_FILE, lines=15)
    print(f"workspace: {WORKSPACE_DIR}")
    print("launching agent — watch agent_progress.txt for TASK:/PROGRESS:/COMPLETE: lines\n")

    rc = launch_agent(context, WORKSPACE_DIR, PROGRESS_FILE)
    print(f"\nlaunch_agent returned {rc}")
    if rc == 0:
        print("✅ Loop complete — check the workspace and agent_progress.txt")
    else:
        print("❌ Agent exited non-zero — check output above")
    sys.exit(0 if rc == 0 else 1)


if __name__ == "__main__":
    main()
