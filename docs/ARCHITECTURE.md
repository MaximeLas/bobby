# Bobby - Complete System Architecture

> **Note:** This is the original design document from Oct 2025. Code samples are design-level pseudocode, not the actual implementation. File paths reference the old `~/Projects/Unicorn` layout. See `CLAUDE.md` in the project root for current structure and conventions.

This document contains the complete technical design, flow diagrams, and implementation details.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Details](#component-details)
3. [Flow Scenarios](#flow-scenarios)
4. [File Structure](#file-structure)
5. [Technology Deep Dive](#technology-deep-dive)
6. [Build Order](#build-order)
7. [Testing Strategy](#testing-strategy)
8. [Migration Path](#migration-path)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│               ZOOM MEETING                              │
│          (Max, Kevin, Michelle)                         │
└────────────┬──────────────────────────▲─────────────────┘
             │                          │
   Audio out │                          │ Audio in
   (speakers)│                          │ (mic)
             │                          │
             ▼                          │
    ┌────────────────┐         ┌───────┴────────┐
    │  BlackHole     │         │   TTS Audio    │
    │  (Audio Cap)   │         │   (Bobby's voice)│
    └────────┬───────┘         └───────▲────────┘
             │                         │
             ▼                         │
    ┌────────────────┐                │
    │  Assembly AI   │                │
    │  (STT)         │                │
    └────────┬───────┘                │
             │                         │
             ▼                         │
    ┌──────────────────────┐          │
    │ meeting_transcript.txt│         │
    └────────┬──────────────┘          │
             │                         │
             ▼                         │
    ┌──────────────────────┐          │
    │  Orchestrator        │          │
    │  (Trigger Detection) │          │
    └────────┬──────────────┘          │
             │                         │
             ├─"Hey Bobby"───────────────┤
             │                         │
             ▼                         │
    ┌──────────────────────┐          │
    │  Claude Code Agent   │          │
    │  (claude -p)         │          │
    └────────┬──────────────┘          │
             │                         │
             ▼                         │
    ┌──────────────────────┐          │
    │ agent_progress.txt   │          │
    └────────┬──────────────┘          │
             │                         │
             ▼                         │
    ┌──────────────────────┐          │
    │  Progress Watcher    │──────────┘
    │  (Speaks Questions)  │
    └──────────────────────┘
```

---

## Component Details

### Component 1: Audio Capture & Transcription

**Purpose:** Convert meeting audio to text in real-time

**Input:** Audio from Zoom meeting (via laptop speakers)
**Output:** `meeting_transcript.txt` (with timestamps and speaker labels)

**Technology:**

- **BlackHole** - Virtual audio device for macOS (routes Zoom audio to Python)
- **PyAudio** - Captures audio stream
- **Assembly AI** - Real-time speech-to-text with speaker identification

**Implementation:**

```python
# audio_capture.py

import pyaudio
import assemblyai as aai
from datetime import datetime

# Configure Assembly AI
aai.settings.api_key = "your-api-key"

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def get_blackhole_device_index():
    """Find BlackHole audio device"""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if 'BlackHole' in info['name']:
            return i
    raise Exception("BlackHole not found. Install it first.")

def on_transcript(transcript: aai.RealtimeTranscript):
    """Callback when transcript chunk arrives"""
    if not transcript.text:
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    speaker = f"Speaker {transcript.speaker}" if transcript.speaker else "Unknown"

    # Append to transcript file
    with open('meeting_transcript.txt', 'a') as f:
        f.write(f"[{timestamp}] {speaker}: {transcript.text}\n")

    print(f"[{timestamp}] {speaker}: {transcript.text}")

def main():
    # Set up audio stream
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=get_blackhole_device_index(),
        frames_per_buffer=CHUNK
    )

    # Set up Assembly AI transcriber
    transcriber = aai.RealtimeTranscriber(
        sample_rate=RATE,
        on_data=on_transcript,
        on_error=lambda error: print(f"Error: {error}")
    )

    transcriber.connect()
    print("🎤 Listening to meeting audio...")

    try:
        while True:
            data = stream.read(CHUNK)
            transcriber.stream(data)
    except KeyboardInterrupt:
        print("\n👋 Stopping transcription...")
    finally:
        transcriber.close()
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()
```

**Setup Steps:**

1. Install BlackHole: `brew install blackhole-2ch`
2. Configure Audio MIDI Setup to route Zoom → BlackHole
3. Install dependencies: `pip install pyaudio assemblyai`
4. Run script: `python bobby/audio_capture.py`

**Output Format:**

```
[14:23:15] Speaker A: So we need a pricing page
[14:23:22] Speaker B: Yeah three tiers would be good
[14:23:35] Speaker A: Hey Bobby, please build this
```

**Difficulty:** 🟡 Medium (3-4 hours including BlackHole setup)

---

### Component 2: Trigger Detection & Orchestration

**Purpose:** Watch transcript, detect triggers, launch/resume Claude Code

**Input:** `meeting_transcript.txt` (continuously updated)
**Output:** Launches Claude Code sessions, manages lifecycle

**Triggers:**

- **"Hey Bobby, please build this"** → Extract context, launch agent
- **"Thank you, Bobby"** → Extract answer, resume agent

**Implementation:**

```python
# orchestrator.py

import subprocess
import time
import os
from datetime import datetime

TRANSCRIPT_FILE = 'meeting_transcript.txt'
PROGRESS_FILE = 'agent_progress.txt'

class Orchestrator:
    def __init__(self):
        self.last_position = 0
        self.agent_running = False
        self.last_trigger_time = 0

    def get_recent_context(self, lines=10):
        """Get last N lines from transcript"""
        try:
            with open(TRANSCRIPT_FILE, 'r') as f:
                return '\n'.join(f.readlines()[-lines:])
        except FileNotFoundError:
            return ""

    def extract_answer(self, text):
        """Extract answer between question and 'thank you bobby'"""
        # Find the last occurrence of question before "thank you bobby"
        # Extract everything in between
        lower_text = text.lower()
        thank_you_index = lower_text.rfind('thank you bobby')

        if thank_you_index == -1:
            return text.strip()

        # Get text before "thank you bobby"
        before_trigger = text[:thank_you_index]

        # Find last line break before trigger
        lines = before_trigger.split('\n')
        # Return last 1-2 lines (the answer)
        return '\n'.join(lines[-2:]).strip()

    def speak_bob(self, text):
        """Make Bobby speak (imports from tts.py)"""
        from tts import speak
        speak(text)

    def launch_agent(self, context):
        """Launch Claude Code agent with task"""
        print("🚀 Launching agent...")

        # Clear progress file
        with open(PROGRESS_FILE, 'w') as f:
            f.write("")

        # Build initial prompt
        prompt = f"""
You are Bobby, an AI assistant helping in a live product meeting.

Recent meeting discussion:
{context}

Task: Build the feature requested in the discussion above.

As you work, write updates to @agent_progress.txt in this format:
- PROGRESS: → Doing something...
- PROGRESS:   ✓ Completed step
- QUESTION: Your question (then stop and wait)
- COMPLETE: Summary + URL

If you need clarification, write QUESTION and stop.
Otherwise, complete the task autonomously.

Deploy to localhost (Vite will auto-reload) or Vercel preview branch.
        """.strip()

        # Run Claude Code
        self.agent_running = True
        subprocess.run(['claude', '-p', prompt])
        self.agent_running = False

        print("✅ Agent execution complete")

    def resume_agent(self, answer):
        """Resume Claude Code with answer"""
        print(f"🔄 Resuming agent with answer: {answer}")

        prompt = f"""
The answer to your question is: {answer}

Please continue with the task.
        """.strip()

        self.agent_running = True
        subprocess.run(['claude', '-p', '--continue', prompt])
        self.agent_running = False

        print("✅ Agent resumed and complete")

    def watch_transcript(self):
        """Main loop - watch transcript for triggers"""
        print("👀 Watching transcript for triggers...")

        while True:
            if not os.path.exists(TRANSCRIPT_FILE):
                time.sleep(1)
                continue

            with open(TRANSCRIPT_FILE, 'r') as f:
                f.seek(self.last_position)
                new_content = f.read()
                self.last_position = f.tell()

            if not new_content:
                time.sleep(1)
                continue

            lower_content = new_content.lower()

            # Trigger 1: Launch agent
            if 'hey bobby, please build this' in lower_content:
                # Debounce (ignore if triggered in last 30 seconds)
                if time.time() - self.last_trigger_time < 30:
                    print("⏭️ Ignoring trigger (debounced)")
                    continue

                self.last_trigger_time = time.time()

                print("🎯 Trigger detected: 'Hey Bobby, please build this'")

                # Bobby acknowledges
                self.speak_bob("Sure, working on it now")

                # Get context and launch
                context = self.get_recent_context(lines=15)
                self.launch_agent(context)

            # Trigger 2: Resume with answer
            elif 'thank you bobby' in lower_content or 'thank you, bobby' in lower_content:
                if not self.agent_running:
                    print("🎯 Trigger detected: 'Thank you, Bobby'")

                    # Extract answer
                    answer = self.extract_answer(new_content)

                    # Resume agent
                    self.resume_agent(answer)

            time.sleep(1)

if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.watch_transcript()
```

**Difficulty:** 🟢 Easy (2-3 hours)

---

### Component 3: Code Execution Agent

**Purpose:** Execute the actual coding task

**Input:** Initial prompt with meeting context
**Output:** Code changes + writes to `agent_progress.txt`

**Technology:** Claude Code CLI (`claude -p`)

**System Prompt:**

This will eventually go in a separate CLAUDE.md for Bobby's execution (not the current one). For now, we pass it via the initial prompt.

```markdown
You are Bobby, an AI developer executing tasks from live product meetings.

## Context

- Participants: Max (developer), Michelle (designer), Kevin (business)
- You receive conversational requests, not formal prompts
- Meeting transcript in @meeting_transcript.txt
- Your workspace is Max's startup project (Vite + React)

## Your Job

1. Read the meeting discussion to understand the task
2. Research the codebase to find where changes should go
3. Build the feature following existing patterns
4. Test your changes
5. Deploy to localhost
6. Report completion with URL (localhost:5173)

## Progress Reporting

Write to @agent_progress.txt as you work:

**Format:**
PROGRESS: → Doing something...
PROGRESS: ✓ Completed step
QUESTION: Your specific question
COMPLETE: Brief summary + URL

**Examples:**
PROGRESS: → Reading codebase structure...
PROGRESS: ✓ Found components in src/components/
PROGRESS: → Creating PricingTable.tsx...
PROGRESS: ✓ Component created
QUESTION: Should the default tier be monthly or annual?

## Questions

When you need clarification:

1. Write: QUESTION: [Your specific question]
2. Then STOP (exit) - you'll be resumed with the answer
3. Don't continue past a question

When resumed, the answer will be in the next prompt.

## Deployment

**Option 1 (Preferred for MVP):**

- Changes are auto-applied (Vite hot reload)
- User will see them immediately in browser
- Report: COMPLETE: Feature added. Visible on localhost:5173

**Option 2 (Optional):**

- Create branch: `git checkout -b feature/[name]`
- Commit changes
- Push to GitHub
- Vercel auto-deploys preview
- Report: COMPLETE: Deployed to [vercel-preview-url]

## Error Handling

If you encounter errors you can't resolve:

- Write: ERROR: [Brief description of issue]
- Don't fail silently
- User will decide whether to try again

## Important

- Be autonomous but ask questions when genuinely unclear
- Follow existing code patterns (check other components)
- Write tests if similar files have tests
- Keep changes minimal and focused
- NEVER deploy to production
```

**Agent Behavior:**

- Reads `@meeting_transcript.txt` to understand task
- Researches codebase using Read, Glob, Grep tools
- Makes changes using Edit, Write tools
- Runs tests using Bash tool
- Deploys (git push or just relies on Vite hot reload)
- Writes progress updates throughout

**Difficulty:** 🟡 Medium (prompt iteration is the challenge, 4-6 hours)

---

### Component 4: Progress Watcher & Voice Output

**Purpose:** Display progress in real-time, make Bobby speak

**Input:** `agent_progress.txt` (written by agent)
**Output:** Console display + TTS audio

**Implementation:**

```python
# progress_watcher.py

import time
import os
from tts import speak

PROGRESS_FILE = 'agent_progress.txt'

def watch_progress():
    """Watch progress file and speak questions/completions"""

    last_position = 0
    print("👀 Watching agent progress...")

    while True:
        if not os.path.exists(PROGRESS_FILE):
            time.sleep(0.5)
            continue

        with open(PROGRESS_FILE, 'r') as f:
            f.seek(last_position)
            new_content = f.read()
            last_position = f.tell()

        if not new_content:
            time.sleep(0.5)
            continue

        for line in new_content.strip().split('\n'):
            if not line:
                continue

            if line.startswith('PROGRESS:'):
                # Just display (don't speak - too many interruptions)
                print(f"[Bobby] {line}")

            elif line.startswith('QUESTION:'):
                question = line.replace('QUESTION:', '').strip()
                print(f"[Bobby asks] {question}")
                speak(question)

            elif line.startswith('COMPLETE:'):
                completion = line.replace('COMPLETE:', '').strip()
                print(f"[Bobby] {completion}")
                speak(completion)

            elif line.startswith('ERROR:'):
                error = line.replace('ERROR:', '').strip()
                print(f"[Bobby - Error] {error}")
                speak(f"I ran into an issue: {error}")

        time.sleep(0.5)

if __name__ == "__main__":
    watch_progress()
```

**TTS Implementation:**

```python
# tts.py

from elevenlabs import generate, play, set_api_key
import os

# Configure ElevenLabs
set_api_key(os.getenv('ELEVENLABS_API_KEY'))

def speak(text):
    """Convert text to speech and play"""
    print(f"🗣️ Bobby speaking: {text}")

    try:
        audio = generate(
            text=text,
            voice="Adam",  # Or "Antoni", "Josh", etc.
            model="eleven_monolingual_v1"
        )

        play(audio)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        print(f"   Fallback: {text}")
```

**Alternative (OpenAI TTS):**

```python
# tts.py (OpenAI version)

import openai
import sounddevice as sd
import numpy as np
from io import BytesIO
from pydub import AudioSegment

openai.api_key = os.getenv('OPENAI_API_KEY')

def speak(text):
    """Convert text to speech using OpenAI TTS"""
    print(f"🗣️ Bobby speaking: {text}")

    try:
        response = openai.audio.speech.create(
            model="tts-1",
            voice="onyx",  # or "alloy", "echo", "fable", "nova", "shimmer"
            input=text
        )

        # Convert to audio and play
        audio_bytes = BytesIO(response.content)
        audio = AudioSegment.from_mp3(audio_bytes)

        # Play
        samples = np.array(audio.get_array_of_samples())
        sd.play(samples, samplerate=audio.frame_rate)
        sd.wait()

    except Exception as e:
        print(f"❌ TTS Error: {e}")
        print(f"   Fallback: {text}")
```

**Difficulty:** 🟢 Easy (2-3 hours)

---

## Flow Scenarios

### Scenario 1: Simple Task (No Questions)

```
Timeline:
00:00 - Meeting starts
00:15 - Max: "We need a pricing table"
00:23 - Michelle: "Three tiers, matches our design system"
00:35 - Max: "Hey Bobby, please build this"

→ Orchestrator detects trigger
→ Bobby speaks: "Sure, working on it now"
→ Orchestrator launches: claude -p "[prompt with context]"

[Agent works for 3 minutes]

agent_progress.txt updates in real-time:
00:36 - PROGRESS: → Reading codebase structure...
00:37 - PROGRESS:   ✓ Found src/components/ directory
00:37 - PROGRESS: → Creating PricingTable.tsx...
00:38 - PROGRESS:   ✓ Component created
00:38 - PROGRESS: → Integrating with design system...
00:39 - PROGRESS:   ✓ Using existing Card and Button components
00:39 - PROGRESS: → Adding to landing page...
00:40 - PROGRESS:   ✓ Imported in Landing.tsx
00:40 - PROGRESS: → Testing...
00:41 - PROGRESS:   ✓ Component renders correctly
00:41 - COMPLETE: Pricing table added. Visible on localhost:5173

→ Progress watcher sees COMPLETE
→ Bobby speaks: "Pricing table added. Visible on localhost:5173"

00:42 - Max: (shares screen, shows new pricing table)
00:42 - Kevin & Michelle: 🤯
```

**Total time: ~6 minutes from request to demo**

---

### Scenario 2: Task with Question

```
Timeline:
00:00 - Max: "Hey Bobby, please build this - add a contact form"

→ Bobby speaks: "Sure, working on it now"
→ Agent launches

[Agent works for 2 minutes]

agent_progress.txt:
00:01 - PROGRESS: → Creating ContactForm component...
00:01 - PROGRESS:   ✓ Form fields added (name, email, message)
00:02 - PROGRESS: → Setting up email submission...
00:02 - QUESTION: Should I use SendGrid or the existing email service?

[Agent exits after writing QUESTION]

→ Progress watcher sees QUESTION
→ Bobby speaks: "Should I use SendGrid or the existing email service?"

00:02:30 - Max: "Use the existing service. Thank you, Bobby."

→ Orchestrator detects "Thank you, Bobby"
→ Extracts answer: "Use the existing service"
→ Resumes: claude -p --continue "Answer: Use the existing service"

[Agent continues for 2 more minutes]

agent_progress.txt:
00:03 - PROGRESS: → Integrating with existing email service...
00:03 - PROGRESS:   ✓ Found API at src/services/email.ts
00:04 - PROGRESS:   ✓ Email handler implemented
00:04 - PROGRESS: → Testing form submission...
00:05 - PROGRESS:   ✓ Test email sent successfully
00:05 - COMPLETE: Contact form added. Visible on localhost:5173/contact

→ Bobby speaks: "Contact form added. Visible on localhost:5173/contact"
```

**Total time: ~5 minutes (with question pause)**

---

## File Structure

```
/Users/maximelas/Projects/Unicorn/
├── CLAUDE.md                   # This project's instructions
├── ARCHITECTURE.md             # This file
├── PROGRESS.md                 # Build status tracking
├── meeting_transcript.txt      # Live transcript (Component 1 writes)
├── agent_progress.txt          # Agent progress (Component 3 writes)
├── bobby/
│   ├── __init__.py
│   ├── audio_capture.py        # Component 1
│   ├── orchestrator.py         # Component 2
│   ├── progress_watcher.py     # Component 4
│   ├── tts.py                  # Voice synthesis
│   └── utils.py                # Shared helpers
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not committed)
└── tests/
    ├── test_transcript.txt     # Mock transcript for testing
    └── test_orchestrator.py    # Unit tests
```

---

## Technology Deep Dive

### Assembly AI Configuration

**Features we use:**

- Real-time streaming transcription
- Speaker labels (diarization)
- Punctuation
- Timestamps

**Configuration:**

```python
aai.TranscriptionConfig(
    speaker_labels=True,
    punctuate=True,
    format_text=True
)
```

**Cost:** ~$0.0043/minute (very affordable)

---

### Claude Code CLI Options

**Key flags:**

- `-p` - Print mode (non-interactive)
- `--continue` - Resume most recent session
- `--resume [id]` - Resume specific session (if needed later)
- `--output-format json` - Not needed for MVP
- `--system-prompt` - Custom system prompt (may use for Bobby-specific instructions)

**Session management:**

```bash
# Launch
claude -p "Build pricing table"

# Resume
claude -p --continue "Answer: Blue button"
```

---

### ElevenLabs Voice Options

**Recommended voices:**

- **Adam** - Professional, clear
- **Antoni** - Warm, friendly
- **Josh** - Deep, authoritative

**Test before choosing:** Use ElevenLabs playground to preview

---

## Build Order

### Day 1: Foundation (4-6 hours)

**Morning:**

1. Set up project structure

   ```bash
   mkdir bobby
   touch bobby/audio_capture.py
   touch bobby/orchestrator.py
   touch bobby/progress_watcher.py
   touch bobby/tts.py
   ```

2. Install BlackHole

   ```bash
   brew install blackhole-2ch
   ```

3. Configure Audio MIDI Setup (route Zoom → BlackHole)

4. Install Python dependencies

   ```bash
   pip install pyaudio assemblyai elevenlabs sounddevice python-dotenv
   ```

5. Set up API keys in `.env`
   ```
   ASSEMBLYAI_API_KEY=your_key
   ELEVENLABS_API_KEY=your_key
   ```

**Afternoon:** 6. Implement Component 1 (audio capture) 7. Test with Zoom recording 8. Verify transcript quality

**Success criteria:** Real-time transcript appears in `meeting_transcript.txt`

---

### Day 2: Agent & Orchestration (6-8 hours)

**Morning:**

1. Write comprehensive system prompt for agent
2. Create test transcript manually:

   ```
   [00:00:00] Speaker A: We need a button on the homepage
   [00:00:10] Speaker A: Hey Bobby, please build this
   ```

3. Test agent manually:

   ```bash
   claude -p "You are Bobby... [system prompt]

   Task: Add button to homepage based on meeting discussion"
   ```

4. Verify agent writes to `agent_progress.txt`
5. Iterate on prompts until agent behaves correctly

**Afternoon:** 6. Implement Component 2 (orchestrator) 7. Test trigger detection with mock transcript 8. Test agent launch flow 9. Test resume flow (simulate question/answer)

**Success criteria:**

- "Hey Bobby, please build this" launches agent
- Agent writes progress updates
- "Thank you, Bobby" resumes agent with answer

---

### Day 3: Voice & Integration (4-6 hours)

**Morning:**

1. Implement Component 4 (progress watcher)
2. Implement TTS (ElevenLabs)
3. Test voice output with manual progress file writes

**Afternoon:** 4. Run all components together (end-to-end) 5. Test with real Zoom meeting audio (just you talking) 6. Debug issues 7. Polish error handling

**Success criteria:**

- Full flow works from audio capture → trigger → agent → completion → voice

---

### Day 4: Polish & Demo (2-4 hours)

1. Add error handling
2. Add logging
3. Test edge cases (interrupted audio, bad triggers, agent errors)
4. Dress rehearsal (full meeting simulation)
5. **Demo to Kevin & Michelle!** 🎉

---

## Testing Strategy

### Component Testing

**Test Component 1 (Audio Capture):**

```bash
# Run audio capture
python bobby/audio_capture.py

# In another window, play audio or join Zoom meeting
# Verify transcript appears in meeting_transcript.txt
```

**Test Component 3 (Agent) with Mock Input:**

```bash
# Create mock transcript
echo "[00:00:00] Speaker A: Add a button to homepage
[00:00:10] Speaker A: Hey Bobby, please build this" > meeting_transcript.txt

# Run agent manually
claude -p "You are Bobby... [full prompt]"

# Check agent_progress.txt for updates
tail -f agent_progress.txt
```

**Test Component 4 (Progress Watcher):**

```bash
# Manually write to progress file
echo "PROGRESS: → Testing..." >> agent_progress.txt
echo "QUESTION: Is this working?" >> agent_progress.txt
echo "COMPLETE: Test complete" >> agent_progress.txt

# Run watcher
python bobby/progress_watcher.py

# Verify Bobby speaks questions and completions
```

---

### Integration Testing

**Test Components 1+2 (Audio → Trigger):**

1. Run audio capture: `python bobby/audio_capture.py`
2. Run orchestrator: `python bobby/orchestrator.py`
3. Speak "Hey Bobby, please build this" into mic
4. Verify trigger detected and agent launches

**Test Components 3+4 (Agent → Progress → Voice):**

1. Run progress watcher: `python bobby/progress_watcher.py`
2. Run agent manually (writes to progress file)
3. Verify progress updates appear
4. Verify Bobby speaks questions and completions

---

### End-to-End Testing

**Full System Test:**

1. Start all components:

   ```bash
   # Terminal 1
   python bobby/audio_capture.py

   # Terminal 2
   python bobby/orchestrator.py

   # Terminal 3
   python bobby/progress_watcher.py
   ```

2. Join Zoom meeting (or start recording)

3. Say: "We need to change the homepage title. Hey Bobby, please build this."

4. Verify:
   - ✅ Transcript appears
   - ✅ Trigger detected
   - ✅ Bobby acknowledges ("Sure, working on it now")
   - ✅ Agent launches and works
   - ✅ Progress updates visible
   - ✅ Agent completes
   - ✅ Bobby announces completion

5. Check localhost:5173 for changes

---

## Migration Path: Local → Discord

When ready to upgrade from local mic to Discord bot:

### What Stays the Same (90%)

- ✅ Assembly AI integration
- ✅ Trigger detection logic
- ✅ Orchestrator
- ✅ Claude Code agent
- ✅ Progress file system
- ✅ All business logic

### What Changes

**Replace Component 1 (Audio Input):**

```python
# OLD: audio_capture.py (BlackHole)
import pyaudio
stream = pyaudio.open(blackhole_device)
audio = stream.read()
assembly_ai.stream(audio)

# NEW: discord_bot.py
import discord

class AudioSink(discord.sinks.Sink):
    def write(self, data):
        assembly_ai.stream(data)

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel:
        vc = await after.channel.connect()
        vc.listen(AudioSink())
```

**Replace TTS Output:**

```python
# OLD: tts.py (local speakers)
import sounddevice as sd
sd.play(audio)

# NEW: tts.py (Discord)
import discord
audio_file = generate_tts(text)
vc.play(discord.FFmpegPCMAudio(audio_file))
```

**Add Discord Chat (Bonus):**

```python
# Send progress updates to Discord chat
@bot.event
async def on_progress_update(line):
    if line.startswith('PROGRESS:'):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send(f"🤖 Bobby: {line}")
```

**Effort:** 1-2 hours to migrate, plus Discord bot setup (~2 hours)

---

## Open Questions / Decisions Needed

- [ ] Debounce timing for triggers (currently 30s - is this enough?)
- [ ] How many lines of context to send to agent? (currently 15 lines)
- [ ] Should Bobby announce when starting work on a task, or just acknowledge?
- [ ] Error recovery strategy (if agent fails, retry automatically or wait for user?)
- [ ] Logging verbosity (how much should we log to console?)

---

## Success Metrics

**MVP Success:**

- ✅ Bobby completes 1 task successfully in demo
- ✅ Total time <5 minutes from request to completion
- ✅ Kevin & Michelle are impressed
- ✅ No manual intervention needed (besides triggers)

**Stretch Goals:**

- ✅ Bobby handles question/answer flow
- ✅ Multiple tasks in one meeting
- ✅ Progress updates visible and helpful
- ✅ Migration to Discord completed

---

## Future Enhancements (Post-MVP)

1. **Multiple Bobs** - Different agents for different tasks (design, backend, testing)
2. **Proactive suggestions** - "I noticed you mentioned X, should I build it?"
3. **Cost optimization** - Batch transcription, cheaper TTS
4. **Better error recovery** - Automatic retries with adjusted prompts
5. **Visual presence** - Avatar in Discord, animated reactions
6. **Integration with tools** - Linear, Notion, Figma
7. **Meeting summaries** - Auto-generated action items
8. **Voice cloning** - Custom voice for Bobby

---

**This architecture is solid, achievable, and exciting. Let's build it! 🚀**
