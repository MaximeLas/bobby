# Prompt for Next Agent

Hi! I'm continuing work on **Bobby** - an AI assistant that joins meetings and builds features in real-time.

## Current State

Bobby works for solo testing! I can speak into my mic, say "Hey Bobby, please build this," and Bobby:

1. Responds with voice: "On it, building now"
2. Launches a Claude agent
3. Builds the feature from meeting context

**What's working:**

- Audio capture (microphone → Assembly AI → transcript)
- Orchestrator (detects triggers, launches agents)
- Voice acknowledgment (macOS say command)
- All scripts renamed Bob → Bobby

## The Problem

The project is a **mess**:

- 18 markdown files (many outdated/duplicate)
- Files scattered between root and test-workspace
- Two venvs (unclear why)
- Old test files everywhere

## What I Need Help With

**Please read [HANDOVER.md](HANDOVER.md) first** - it has complete details.

**Then, I'd like you to help with ONE of these (I'll tell you which):**

### Option A: Project Cleanup (Recommended)

Make this project maintainable:

- Delete/consolidate the 18 markdown files
- Organize code properly
- Clean up venvs
- Remove old test files
- Update remaining docs to be accurate

### Option B: Finalize Audio for Zoom (or Discord meetings, which should be easier to implement with Discord's API)

Set up aggregate device so Bobby works in real Zoom meetings:

- Create aggregate device (mic + BlackHole)
- Test with Zoom
- Document the setup

### Option C: Integrate ElevenLabs TTS

Replace macOS say with natural-sounding voice

---

**Let's start with: [Max will tell you which option]**

After reading HANDOVER.md, let me know you understand the current state and we'll proceed!
