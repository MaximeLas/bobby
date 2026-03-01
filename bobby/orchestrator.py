#!/usr/bin/env python3
"""
Bobby Orchestrator - Component 2
Watches meeting transcript, detects triggers, launches/resumes Claude Code agents
"""

import subprocess
import time
import os
import sys
from datetime import datetime

from bobby.config import TRANSCRIPT_FILE, PROGRESS_FILE, PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE, WORKSPACE_DIR

# Debounce window (seconds)
DEBOUNCE_SECONDS = 30

# Polling interval (seconds)
POLL_INTERVAL = 1


class Orchestrator:
    """
    Orchestrator watches meeting_transcript.txt for triggers and manages Claude Code agents.

    Triggers:
    - "Hey Bobby, please build this" -> Launch new agent
    - "Thank you, Bobby" -> Resume agent with answer
    """

    def __init__(self, test_voice_only=False):
        self.agent_running = False
        self.last_trigger_time = 0
        self.test_voice_only = test_voice_only

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
        try:
            with open(TRANSCRIPT_FILE, 'r') as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return ''.join(recent)
        except FileNotFoundError:
            print(f"Warning: {TRANSCRIPT_FILE} not found")
            return ""
        except Exception as e:
            print(f"Error reading transcript: {e}")
            return ""

    def extract_answer(self, text):
        """
        Extract answer between question and 'thank you bobby'.

        This function attempts to find the answer provided by the user
        after Bobby asks a question and before they say "thank you bobby".

        Args:
            text: Text containing the answer and trigger phrase

        Returns:
            Extracted answer text
        """
        lower_text = text.lower()

        # Find "thank you bobby" trigger
        thank_you_variants = ['thank you, bobby', 'thank you bobby', 'thanks bobby']
        trigger_index = -1

        for variant in thank_you_variants:
            idx = lower_text.rfind(variant)
            if idx != -1:
                trigger_index = idx
                break

        if trigger_index == -1:
            # No trigger found, return the whole text as answer
            return text.strip()

        # Get text before "thank you bobby"
        before_trigger = text[:trigger_index]

        # Split into lines and get the last few (the answer)
        lines = before_trigger.split('\n')
        # Filter out empty lines
        non_empty = [line.strip() for line in lines if line.strip()]

        # Return last 1-3 lines as the answer
        answer_lines = non_empty[-3:] if len(non_empty) >= 3 else non_empty
        return '\n'.join(answer_lines).strip()

    def speak_bob(self, text):
        """
        Make Bobby speak using ElevenLabs TTS with Eastern European accent.

        Pauses transcription while Bobby speaks to prevent capturing Bobby's own voice.

        Args:
            text: What Bobby should say
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'=' * 60}")
        print(f"[{timestamp}] 🗣️  Bobby says: {text}")
        print(f"{'=' * 60}\n")

        # Create pause flag to stop audio_capture.py from transcribing Bobby's voice
        try:
            with open(PAUSE_FLAG_FILE, 'w') as f:
                f.write(f"Paused for Bobby speech at {timestamp}\n")
            print(f"[DEBUG] Created pause flag: {PAUSE_FLAG_FILE}")
        except Exception as e:
            print(f"Warning: Could not create pause flag: {e}")

        # Use ElevenLabs TTS with Bobby's Eastern European voice
        try:
            # Import tts from same directory (both in bobby/ folder)
            from bobby.tts import speak
            print(f"[DEBUG] Using ElevenLabs TTS with Eastern European voice")
            speak(text)
            print(f"[DEBUG] ElevenLabs TTS completed successfully")
        except Exception as e:
            print(f"❌ ERROR: ElevenLabs TTS failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to macOS say command
            print(f"[DEBUG] Falling back to macOS 'say' command")
            try:
                subprocess.run(
                    ['say', '-v', 'Alex', text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10
                )
            except Exception as fallback_error:
                print(f"Warning: Fallback TTS also failed: {fallback_error}")

        # Remove pause flag to resume transcription
        try:
            if os.path.exists(PAUSE_FLAG_FILE):
                os.remove(PAUSE_FLAG_FILE)
                print(f"[DEBUG] Removed pause flag, transcription resumed")
        except Exception as e:
            print(f"Warning: Could not remove pause flag: {e}")

        # Store what Bobby said so audio_capture can filter it out
        # (Assembly AI buffers audio during pause and sends it after)
        try:
            with open(str(BOBBY_SPEECH_FILE), 'w') as f:
                f.write(text.lower())
        except Exception as e:
            print(f"Warning: Could not write Bobby's speech: {e}")

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

        # Add session marker (don't clear file - keep history like transcript)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(PROGRESS_FILE, 'a') as f:
                f.write(f"\n=== New Agent Session: {timestamp} ===\n\n")
            print(f"Started new session in {PROGRESS_FILE}")
        except Exception as e:
            print(f"Error writing to progress file: {e}")

        # Build prompt with meeting context reference
        prompt = f"""You are Bobby, an AI assistant helping in a live product meeting.

Recent meeting discussion:
{context}

Task: Build the feature requested in the discussion above.

IMPORTANT: The transcript may contain multiple speakers (Max, Michelle, Kevin) but without speaker labels.
Pay attention to conversational context to understand who is saying what and what the requirements are.

As you work, write LIVE updates to @agent_progress.txt in this format:
- PROGRESS: -> Doing something...
- PROGRESS:   ✓ Completed step
- QUESTION: Your question (then stop and wait)
- COMPLETE: Summary + URL

CRITICAL INSTRUCTIONS FOR PROGRESS UPDATES:

Write progress updates to @agent_progress.txt using EXACTLY this format:

1. FIRST: Immediately write this EXACT line: "PROGRESS: -> Starting task"
2. Do some work
3. Write ONE line: "PROGRESS:   ✓ [what you completed]"
4. Do more work
5. Write ONE line: "COMPLETE: [summary] at http://localhost:5173"

STRICT RULES:
- Each Write operation = EXACTLY ONE LINE starting with "PROGRESS:" or "COMPLETE:" or "QUESTION:"
- NO empty lines, NO numbered lists, NO markdown formatting
- ALWAYS use append mode (never overwrite the file)
- Write 3-5 updates total (not 20+)

Example - THREE separate Write operations:
  Write #1:  "PROGRESS: -> Starting task"
  Write #2:  "PROGRESS: -> Analyzing requirements"
  Write #3:  "PROGRESS:   ✓ Created component"
  Write #4:  "PROGRESS: -> Testing component"
  Write #5:  "PROGRESS:   ✓ Component tested"
  Write #6:  "COMPLETE: Feature live at http://localhost:5173"

WRONG (do NOT do this):
  - Writing empty lines
  - Writing "1. Task" or numbered lists
  - Writing multiple PROGRESS lines in one Write operation
  - Clearing or overwriting the file

If you need clarification, write QUESTION and stop.
Otherwise, complete the task autonomously.

Deploy to localhost (Vite will auto-reload).
Reference the full meeting transcript at @meeting_transcript.txt if you need more context."""

        # Run Claude Code in target workspace directory with permissions
        print("Executing: claude -p --dangerously-skip-permissions [prompt]")
        print(f"Working directory: {WORKSPACE_DIR}")
        print("Agent is now running...\n")

        self.agent_running = True

        try:
            result = subprocess.run(
                ['claude', '-p', '--dangerously-skip-permissions', prompt],
                capture_output=False,  # Let output go to terminal
                text=True,
                cwd=str(WORKSPACE_DIR)
            )

            print(f"\nAgent process exited with code: {result.returncode}")

        except FileNotFoundError:
            print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        except Exception as e:
            print(f"ERROR launching agent: {e}")
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

        prompt = f"""The answer to your question is: {answer}

Please continue with the task."""

        print("Executing: claude -p --continue [answer]")
        print("Agent is now running...\n")

        self.agent_running = True

        try:
            result = subprocess.run(
                ['claude', '-p', '--dangerously-skip-permissions', '--continue', prompt],
                capture_output=False,  # Let output go to terminal
                text=True,
                cwd=str(WORKSPACE_DIR)
            )

            print(f"\nAgent process exited with code: {result.returncode}")

        except FileNotFoundError:
            print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        except Exception as e:
            print(f"ERROR resuming agent: {e}")
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

                # Check for triggers (case-insensitive)
                lower_content = new_content.lower()

                # Remove all commas and extra spaces to make matching more flexible
                # This handles: "Hey, Bobby, please build this." → "hey bobby please build this"
                normalized_content = ' '.join(lower_content.replace(',', '').replace('.', '').split())
                print(f"[DEBUG] Normalized content: {normalized_content[:100]!r}")
                print(f"[DEBUG] Checking for 'hey bobby please build this' trigger")

                # Trigger 1: Launch agent
                if 'hey bobby please build this' in normalized_content:
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
                    self.speak_bob("Very nice! I build for you now. Great success!")

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
                elif 'thank you bobby' in normalized_content or 'thanks bobby' in normalized_content:
                    # Only resume if agent was running (asked a question)
                    # For MVP, we'll always try to resume when we see this trigger

                    print(f"\n{'!' * 60}")
                    print("TRIGGER DETECTED: 'Thank you, Bobby'")
                    print(f"{'!' * 60}\n")

                    # Extract answer from content
                    answer = self.extract_answer(new_content)

                    print(f"Extracted answer: {answer}\n")

                    # Resume agent with answer
                    self.resume_agent(answer)

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
