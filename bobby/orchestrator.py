#!/usr/bin/env python3
"""
Bobby Orchestrator - Component 2
Watches meeting transcript, detects triggers, launches/resumes Claude Code agents
"""

import threading
import time
import os
import sys
from datetime import datetime

from bobby.config import TRANSCRIPT_FILE, PROGRESS_FILE, WORKSPACE_DIR, PROACTIVE_ENABLED
from bobby.agent_runner import (
    detect_trigger,
    extract_answer as _extract_answer,
    get_recent_context as _get_recent_context,
    launch_agent as _launch_agent,
    resume_agent as _resume_agent,
)
from bobby.prompts import (
    VOICE_ACKNOWLEDGE_LAUNCH,
    VOICE_ACKNOWLEDGE_RESUME,
    VOICE_BRAIN_ERROR,
)
from bobby.voice import speak_in_meeting

# Debounce window (seconds)
DEBOUNCE_SECONDS = 30

# Converse gets a shorter window: back-to-back questions are legitimate,
# transcript echo double-fires are not (mirrors Discord's 10s)
CONVERSE_DEBOUNCE_SECONDS = 10

# Polling interval (seconds)
POLL_INTERVAL = 1


class Orchestrator:
    """
    Orchestrator watches meeting_transcript.txt for triggers and manages Claude Code agents.

    Triggers:
    - "Hey Bobby, please build this" -> Launch new agent
    - "Thank you, Bobby" -> Resume agent with answer
    - "Hey Bobby, <anything else>" -> Spoken answer from the brain
    """

    def __init__(self, test_voice_only=False):
        self.agent_running = False
        self.last_trigger_time = 0
        self.last_converse_time = 0
        self.test_voice_only = test_voice_only

        # Proactive suggestions (BOBBY_PROACTIVE=1; see bobby/suggestions.py)
        if PROACTIVE_ENABLED:
            from bobby.suggestions import ProactiveEngine
            self.proactive = ProactiveEngine()
        else:
            self.proactive = None

        # Seek to END of file so we only process NEW content (not old triggers)
        if os.path.exists(TRANSCRIPT_FILE):
            with open(TRANSCRIPT_FILE, 'r') as f:
                f.seek(0, 2)  # Seek to end of file (0 bytes from end)
                self.last_position = f.tell()
            print(f"Starting from end of existing transcript (position: {self.last_position})")
        else:
            self.last_position = 0
            print("Transcript file doesn't exist yet, will watch from beginning")

        print("=" * 60)
        if self.test_voice_only:
            print("Bobby Orchestrator - VOICE TEST MODE")
            print("=" * 60)
            print("✅ Will respond with voice")
            print("❌ Will NOT launch agents (saving credits)")
        else:
            print("Bobby Orchestrator - Starting Up")
            print("=" * 60)
        print(f"Watching: {TRANSCRIPT_FILE}")
        print(f"Absolute path: {os.path.abspath(TRANSCRIPT_FILE)}")
        if not self.test_voice_only:
            print(f"Progress: {PROGRESS_FILE}")
        print(f"Debounce: {DEBOUNCE_SECONDS}s")
        print(f"Poll interval: {POLL_INTERVAL}s")
        print("=" * 60)

    def get_recent_context(self, lines=10):
        """
        Get last N lines from transcript for context.

        Args:
            lines: Number of recent lines to retrieve

        Returns:
            String containing recent transcript lines
        """
        return _get_recent_context(TRANSCRIPT_FILE, lines=lines)

    def extract_answer(self, text):
        """
        Extract answer between question and 'thank you bobby'.

        Args:
            text: Text containing the answer and trigger phrase

        Returns:
            Extracted answer text
        """
        return _extract_answer(text)

    def speak_bob(self, text):
        """
        Make Bobby speak using the shared local-mode helper (bobby/voice.py):
        pauses transcription, speaks via ElevenLabs with macOS `say` fallback,
        resumes, and records the utterance for self-speech filtering.

        Args:
            text: What Bobby should say
        """
        speak_in_meeting(text)

    def handle_conversation(self):
        """
        Answer a 'Hey Bobby, ...' utterance with a spoken, transcript-grounded
        reply (see bobby/brain.py). Blocking (LLM call + TTS) — the watch loop
        runs this in a daemon thread so trigger polling continues meanwhile.

        Local-mode limitation: launch_agent() blocks the watch loop, so unlike
        Discord mode a converse trigger can't fire mid-build here — no
        progress tail is passed.
        """
        from bobby.brain import ask_brain

        context = self.get_recent_context(lines=20)
        answer = ask_brain(context)

        if answer:
            self.speak_bob(answer)
        else:
            self.speak_bob(VOICE_BRAIN_ERROR)

    def run_proactive(self, excerpt):
        """
        Run one proactive analysis and speak the offer if one comes back.
        Blocking (LLM + TTS) — the watch loop runs this in a daemon thread.
        """
        suggestion = self.proactive.analyze(excerpt, time.time())
        if suggestion:
            print(f"Proactive suggestion: {suggestion['feature']}")
            self.speak_bob(suggestion["voice_line"])

    def launch_agent(self, context):
        """
        Launch Claude Code agent with task from meeting context.

        Args:
            context: Recent meeting transcript for context
        """
        print("\n" + "=" * 60)
        print("LAUNCHING AGENT")
        print("=" * 60)
        print(f"Context (last {len(context.split(chr(10)))} lines):")
        print(context)
        print("=" * 60 + "\n")

        self.agent_running = True
        try:
            _launch_agent(context, WORKSPACE_DIR, PROGRESS_FILE)
        finally:
            self.agent_running = False

        print("\n" + "=" * 60)
        print("AGENT EXECUTION COMPLETE")
        print("=" * 60 + "\n")

    def resume_agent(self, answer):
        """
        Resume Claude Code with answer to question.

        Args:
            answer: Answer to the agent's question
        """
        print("\n" + "=" * 60)
        print("RESUMING AGENT")
        print("=" * 60)
        print(f"Answer: {answer}")
        print("=" * 60 + "\n")

        self.agent_running = True
        try:
            _resume_agent(answer, WORKSPACE_DIR)
        finally:
            self.agent_running = False

        print("\n" + "=" * 60)
        print("AGENT RESUME COMPLETE")
        print("=" * 60 + "\n")

    def watch_transcript(self):
        """
        Main loop - watch transcript file for triggers.

        Continuously monitors meeting_transcript.txt for:
        - "Hey Bobby, please build this" (launch trigger)
        - "Thank you, Bobby" (resume trigger)
        """
        print("\nStarting transcript watcher...")
        print("Waiting for triggers...\n")

        while True:
            try:
                # Check if transcript file exists
                if not os.path.exists(TRANSCRIPT_FILE):
                    # Wait for file to be created
                    time.sleep(POLL_INTERVAL)
                    continue

                # Read new content from file
                with open(TRANSCRIPT_FILE, 'r') as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    self.last_position = f.tell()

                # No new content, keep waiting
                if not new_content:
                    time.sleep(POLL_INTERVAL)
                    continue

                # Log new content
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] New transcript content ({len(new_content)} chars)")
                print(f"[DEBUG] Content preview: {new_content[:200]!r}")

                # Check for triggers using shared detection logic
                trigger = detect_trigger(new_content)
                print(f"[DEBUG] Trigger detection result: {trigger}")

                # Proactive engine bookkeeping (no-op unless BOBBY_PROACTIVE=1):
                # trigger-free discussion feeds the engine; explicit triggers
                # suppress suggestions for a while.
                if self.proactive is not None:
                    if trigger is None:
                        self.proactive.accumulate(new_content)
                        excerpt = self.proactive.try_begin(
                            time.time(), agent_running=self.agent_running
                        )
                        if excerpt:
                            threading.Thread(
                                target=self.run_proactive,
                                args=(excerpt,),
                                daemon=True,
                            ).start()
                    else:
                        self.proactive.note_activity(time.time())

                # Trigger 1: Launch agent
                if trigger == "launch":
                    # Debounce check
                    time_since_last = time.time() - self.last_trigger_time

                    if time_since_last < DEBOUNCE_SECONDS:
                        print(f"\nIgnoring trigger (debounced - {time_since_last:.1f}s < {DEBOUNCE_SECONDS}s)")
                        time.sleep(POLL_INTERVAL)
                        continue

                    # Update trigger time
                    self.last_trigger_time = time.time()

                    print(f"\n{'!' * 60}")
                    print("TRIGGER DETECTED: 'Hey Bobby, please build this'")
                    print(f"{'!' * 60}\n")

                    # Bobby acknowledges immediately (before agent launch)
                    self.speak_bob(VOICE_ACKNOWLEDGE_LAUNCH)

                    # In test mode, stop here (don't launch agent)
                    if self.test_voice_only:
                        print()
                        print("=" * 60)
                        print("✅ VOICE TEST COMPLETE - Agent NOT launched")
                        print("=" * 60)
                        print()
                        continue

                    # Get context and launch
                    context = self.get_recent_context(lines=15)
                    self.launch_agent(context)

                # Trigger 2: Resume with answer
                elif trigger == "resume":
                    # Only resume if agent was running (asked a question)
                    # For MVP, we'll always try to resume when we see this trigger

                    print(f"\n{'!' * 60}")
                    print("TRIGGER DETECTED: 'Thank you, Bobby'")
                    print(f"{'!' * 60}\n")

                    # Acknowledge before the resume (voice parity with Discord)
                    self.speak_bob(VOICE_ACKNOWLEDGE_RESUME)

                    # Extract answer from content
                    answer = self.extract_answer(new_content)

                    print(f"Extracted answer: {answer}\n")

                    # Resume agent with answer
                    self.resume_agent(answer)

                # Trigger 3: Converse ("Hey Bobby, <anything else>")
                elif trigger == "converse":
                    time_since_last = time.time() - self.last_converse_time

                    if time_since_last < CONVERSE_DEBOUNCE_SECONDS:
                        print(f"\nIgnoring converse trigger (debounced - "
                              f"{time_since_last:.1f}s < {CONVERSE_DEBOUNCE_SECONDS}s)")
                        time.sleep(POLL_INTERVAL)
                        continue

                    self.last_converse_time = time.time()

                    print(f"\n{'!' * 60}")
                    print("TRIGGER DETECTED: converse ('Hey Bobby, ...')")
                    print(f"{'!' * 60}\n")

                    # Fire-and-forget so the watcher keeps polling during the
                    # brain call + TTS (same pattern as Discord mode)
                    threading.Thread(
                        target=self.handle_conversation, daemon=True
                    ).start()

                # Continue polling
                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                print("\n\nShutting down orchestrator...")
                print("Goodbye!\n")
                break
            except Exception as e:
                print(f"\nERROR in main loop: {e}")
                print("Continuing to watch...\n")
                time.sleep(POLL_INTERVAL)


def main():
    """Entry point for orchestrator"""
    # Check for --test-voice flag
    test_voice_only = '--test-voice' in sys.argv

    orchestrator = Orchestrator(test_voice_only=test_voice_only)
    orchestrator.watch_transcript()


if __name__ == "__main__":
    main()
