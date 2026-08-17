#!/usr/bin/env python3
"""
Manual test: one live conversational-brain answer, end to end.

Feeds a fake meeting transcript to bobby.brain.ask_brain and prints the
answer. Uses the real `claude` CLI (fast model) — run from your own
terminal so the CLI can authenticate. ~30 seconds, one cheap LLM call.

Run:  uv run python3 tests/manual/test_brain.py
      uv run python3 tests/manual/test_brain.py "Hey Bobby, your own question?"
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bobby.brain import ask_brain

FAKE_TRANSCRIPT = """[14:02:11] [Max] So for the demo I think we go with the hero page upgrade.
[14:02:19] [David] Agreed, the current one is very basic anyway.
[14:02:27] [Max] {question}"""

DEFAULT_QUESTION = "Hey Bobby, what did we just decide to build for the demo?"


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    context = FAKE_TRANSCRIPT.format(question=question)

    print(f"🗣️  Question: {question}")
    print("🧠 Asking the brain (5-15s via claude CLI)...")
    t0 = time.time()
    answer = ask_brain(context)
    elapsed = time.time() - t0

    if answer:
        print(f"✅ Answer ({elapsed:.1f}s): {answer}")
        print("\nSanity checks: in character? 1-3 sentences? grounded in the transcript?")
    else:
        print(f"❌ Brain returned no answer after {elapsed:.1f}s — check `claude` CLI auth and output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
