# Bobby Orchestrator - Complete Guide

## Overview

The orchestrator is Component 2 of Bobby, the AI meeting assistant. It watches `meeting_transcript.txt` for triggers and manages Claude Code agents.

**Location:** `/Users/maximelas/Projects/Unicorn/bobby/orchestrator.py`

## What It Does

The orchestrator implements the core intelligence of Bobby:

1. **Watches** `meeting_transcript.txt` continuously (polls every 1 second)
2. **Detects** two trigger phrases (case-insensitive):
   - "Hey Bobby, please build this" → Launch new agent with meeting context
   - "Thank you, Bobby" → Resume agent with answer to question
3. **Manages** Claude Code CLI sessions:
   - Launch: `claude -p [prompt]`
   - Resume: `claude -p --continue [answer]`
4. **Provides** verbose logging of all actions

## Quick Start

### 1. Verify Installation

```bash
cd /Users/maximelas/Projects/Unicorn
python3 verify_orchestrator.py
```

All tests should pass.

### 2. Run the Orchestrator

```bash
python3 bobby/orchestrator.py
```

You should see:
```
============================================================
Bobby Orchestrator - Starting Up
============================================================
Watching: meeting_transcript.txt
Progress: agent_progress.txt
Debounce: 30s
Poll interval: 1s
============================================================

Starting transcript watcher...
Waiting for triggers...
```

### 3. Test with Demo

In another terminal:

```bash
./demo_orchestrator.sh
```

This will guide you through a simulated meeting scenario.

## Usage Examples

### Example 1: Launch Agent

**Scenario:** You want Bobby to build a feature

1. Have the orchestrator running
2. Add meeting context to transcript:
   ```bash
   echo "[14:00:00] Max: We need a pricing table" >> meeting_transcript.txt
   echo "[14:00:15] Michelle: Three tiers, matches design system" >> meeting_transcript.txt
   ```
3. Add trigger:
   ```bash
   echo "[14:00:30] Max: Hey Bobby, please build this" >> meeting_transcript.txt
   ```

**What happens:**
- Orchestrator detects trigger
- Prints: "Bobby would say: Sure, working on it now"
- Extracts last 15 lines as context
- Clears `agent_progress.txt`
- Launches: `claude -p [prompt with context]`

**Agent prompt includes:**
- Recent meeting discussion (15 lines)
- Instructions to write progress to `@agent_progress.txt`
- Task description
- Reference to full transcript at `@meeting_transcript.txt`

### Example 2: Resume Agent with Answer

**Scenario:** Bobby asks a question, you provide an answer

1. Agent is running and writes a question:
   ```
   QUESTION: Should the pricing be monthly or annual?
   ```
   (Agent exits after writing QUESTION)

2. Progress watcher (Component 4) makes Bobby speak the question

3. You answer in the meeting:
   ```bash
   echo "[14:03:00] Max: Monthly pricing please" >> meeting_transcript.txt
   echo "[14:03:05] Max: Thank you, Bobby" >> meeting_transcript.txt
   ```

**What happens:**
- Orchestrator detects "Thank you, Bobby"
- Extracts answer: "Monthly pricing please"
- Resumes: `claude -p --continue "Answer: Monthly pricing please"`
- Agent continues working

### Example 3: Debounce Protection

**Scenario:** Accidental double trigger

```bash
echo "[14:00:30] Max: Hey Bobby, please build this" >> meeting_transcript.txt
# (Agent launches)

# 10 seconds later, another person says it
echo "[14:00:40] Kevin: Hey Bobby, please build this" >> meeting_transcript.txt
```

**What happens:**
- First trigger launches agent
- Second trigger is ignored (within 30-second debounce window)
- Orchestrator prints: "Ignoring trigger (debounced - 10.0s < 30s)"

## File Structure

```
/Users/maximelas/Projects/Unicorn/
├── bobby/
│   ├── __init__.py              # Package init
│   ├── orchestrator.py          # Main orchestrator (THIS)
│   ├── tts.py                   # TTS placeholder
│   └── README.md                # Component documentation
├── meeting_transcript.txt       # INPUT: Meeting transcript
├── agent_progress.txt           # OUTPUT: Agent's progress
├── verify_orchestrator.py       # Verification tests
├── test_orchestrator.py         # Interactive test suite
└── demo_orchestrator.sh         # Demo walkthrough
```

## Configuration

### Adjustable Constants

In `bobby/orchestrator.py`:

```python
# File paths
TRANSCRIPT_FILE = 'meeting_transcript.txt'
PROGRESS_FILE = 'agent_progress.txt'

# Debounce window (seconds) - how long to ignore duplicate triggers
DEBOUNCE_SECONDS = 30

# Polling interval (seconds) - how often to check for new content
POLL_INTERVAL = 1
```

### Context Lines

In the `launch_agent()` method:

```python
context = self.get_recent_context(lines=15)  # Adjust number here
```

**Recommendation:**
- 10-15 lines for focused context
- 20-30 lines for more background
- More lines = higher token usage in Claude prompt

## Integration with Other Components

### Component 1: Audio Capture

**Not yet implemented**

Will write to `meeting_transcript.txt` in real-time:
```
[HH:MM:SS] Speaker A: Transcript text here
```

For now, simulate by manually adding lines:
```bash
echo "[14:00:00] Speaker A: Text" >> meeting_transcript.txt
```

### Component 3: Code Execution Agent

**Claude Code CLI**

Orchestrator launches Claude with specific prompts:
- Initial: Includes meeting context, task description, progress instructions
- Resume: Includes answer to question

Agent should write to `agent_progress.txt`:
```
PROGRESS: -> Doing something...
PROGRESS:   ✓ Completed step
QUESTION: Your specific question
COMPLETE: Summary + URL
ERROR: Problem description
```

### Component 4: Progress Watcher

**Not yet implemented**

Will watch `agent_progress.txt` and:
- Display progress updates
- Speak questions and completions via TTS
- Alert on errors

For now, monitor manually:
```bash
tail -f agent_progress.txt
```

## Trigger Detection Details

### Launch Trigger: "Hey Bobby, please build this"

**Variants detected:**
- "hey bobby, please build this" (exact, case-insensitive)
- "hey bobby please build this" (without comma)

**Not detected:**
- "Hey Bobby, build this" (missing "please")
- "Bobby, please build this" (missing "Hey")
- "Hey Bobby can you build this" (different phrasing)

**Why strict matching?**
- Prevents false positives from casual conversation
- Clear, intentional trigger phrase
- Can be relaxed later if needed

**Context extraction:**
- Gets last 15 lines from transcript
- Includes speaker labels and timestamps
- Provides agent with discussion leading up to request

### Resume Trigger: "Thank you, Bobby"

**Variants detected:**
- "thank you, bobby" (case-insensitive)
- "thank you bobby" (no comma)
- "thanks bobby"

**Answer extraction:**
- Finds trigger phrase in new content
- Extracts 1-3 lines before trigger
- Assumes this is the answer to Bobby's question

**Example:**
```
[14:03:00] Max: The answer is blue
[14:03:05] Max: Thank you, Bobby
```
Extracted answer: "The answer is blue"

## Error Handling

### Missing Transcript File

**Behavior:** Orchestrator waits patiently

```
Waiting for triggers...
(keeps polling every second until file appears)
```

**When it appears:** Starts reading from beginning

### Missing Claude CLI

**Behavior:** Prints error, continues watching

```
ERROR: 'claude' command not found. Is Claude Code CLI installed?
```

**Fix:**
1. Install Claude Code CLI
2. Verify: `which claude` returns a path
3. Orchestrator will work on next trigger

### Agent Execution Error

**Behavior:** Logs error, clears agent_running flag

```
ERROR launching agent: [error details]
```

**Recovery:** Orchestrator continues watching for next trigger

### Keyboard Interrupt

**Behavior:** Graceful shutdown

```
^C
Shutting down orchestrator...
Goodbye!
```

## Testing

### Automated Verification

```bash
python3 verify_orchestrator.py
```

Tests:
- Module import
- Class instantiation
- Context extraction
- Answer extraction
- speak_bob() method
- TTS module

### Interactive Test Suite

```bash
python3 test_orchestrator.py
```

Options:
1. Launch agent trigger test
2. Resume agent trigger test
3. Debounce test
4. Manual test mode (add lines interactively)
5. Run all automated tests

### Demo Walkthrough

```bash
./demo_orchestrator.sh
```

Simulates a complete meeting scenario with guided steps.

### Manual Testing

**Terminal 1:** Run orchestrator
```bash
python3 bobby/orchestrator.py
```

**Terminal 2:** Simulate transcript
```bash
# Add context
echo "[14:00:00] Max: We need a homepage hero section" >> meeting_transcript.txt
echo "[14:00:10] Michelle: Make it bold and eye-catching" >> meeting_transcript.txt

# Add trigger
echo "[14:00:20] Max: Hey Bobby, please build this" >> meeting_transcript.txt

# Wait for agent to ask question (check agent_progress.txt)
# Then provide answer
echo "[14:01:30] Max: Use the brand colors from the design system" >> meeting_transcript.txt
echo "[14:01:35] Max: Thank you, Bobby" >> meeting_transcript.txt
```

**Terminal 3:** Monitor progress
```bash
tail -f agent_progress.txt
```

## Troubleshooting

### Trigger not detected

**Check:**
1. Is orchestrator running? (should show startup banner)
2. Is trigger phrase exact? (case-insensitive but spelling matters)
3. Check orchestrator output - does it show new content?
4. Is debounce blocking it? (wait 30 seconds after last trigger)

**Debug:**
```bash
# Enable more logging (modify orchestrator.py temporarily)
print(f"Checking: {lower_content}")  # Add after line 318
```

### Agent doesn't launch

**Check:**
1. Is Claude CLI installed? `which claude`
2. Check orchestrator output for errors
3. Try manually: `claude -p "Test prompt"`

**Common issues:**
- Claude CLI not in PATH
- No active Claude session
- Insufficient permissions

### Answer not extracted correctly

**Check:**
1. Is answer immediately before "Thank you, Bobby"?
2. Multiple speakers? (extracts last 3 lines before trigger)
3. Check orchestrator output: "Extracted answer: ..."

**Adjust if needed:**
Modify `extract_answer()` method in `orchestrator.py`

### Debounce too aggressive

**Issue:** Legitimate triggers being ignored

**Fix:** Reduce debounce window
```python
DEBOUNCE_SECONDS = 15  # Change from 30 to 15
```

**Or:** Wait longer between triggers

## Performance

### Resource Usage

- **CPU:** Minimal (polls file once per second)
- **Memory:** <10 MB (just watching a text file)
- **Disk I/O:** Low (reads only new file content)

### Latency

- **Trigger detection:** ~1 second (poll interval)
- **Context extraction:** <100ms
- **Agent launch:** 2-5 seconds (Claude CLI startup)

**Total delay from trigger to agent start:** ~3-6 seconds

### Scalability

Current implementation is fine for:
- Single meeting
- One agent at a time
- Transcript <1000 lines

For future needs:
- Multiple agents: Track agent IDs
- Large transcripts: Use file seeking efficiently (already done)
- Real-time streaming: Switch from polling to file watching (inotify/fswatch)

## Deviations from ARCHITECTURE.md

### Aligned with Spec

The implementation follows ARCHITECTURE.md Component 2 specifications:

- ✅ Watches `meeting_transcript.txt` continuously
- ✅ Polls every 1 second
- ✅ Tracks file position (only reads new content)
- ✅ Detects "Hey Bobby, please build this" trigger
- ✅ Detects "Thank you, Bobby" trigger
- ✅ Extracts context for launch (15 lines)
- ✅ Extracts answer for resume
- ✅ Launches `claude -p` with prompt
- ✅ Resumes `claude -p --continue` with answer
- ✅ 30-second debounce protection
- ✅ Verbose logging
- ✅ Error handling for missing files
- ✅ Uses `speak_bob()` placeholder for TTS

### Minor Differences

1. **TTS Integration:**
   - Spec: Import from `tts.py`
   - Implementation: Placeholder in orchestrator, comment shows future integration
   - Reason: TTS not yet implemented, easier to see what Bobby would say for testing

2. **Prompt Format:**
   - Spec: Basic example
   - Implementation: More detailed with explicit instructions for agent
   - Reason: Better agent behavior with clearer instructions

3. **Context Lines:**
   - Spec: Not specified
   - Implementation: 15 lines (configurable)
   - Reason: Good balance between context and token usage

4. **Error Recovery:**
   - Spec: "Handle missing files gracefully"
   - Implementation: Detailed error handling with continued operation
   - Reason: Robust operation during development and integration

### Future Enhancements

Not in current implementation but mentioned in ARCHITECTURE.md:

- **Multiple agents:** Currently one at a time
- **Agent state tracking:** Basic flag, not persistent
- **Resume by session ID:** Uses `--continue` (latest session)
- **Discord integration:** Not yet (MVP uses local files)

## Next Steps

### Immediate (This Session)

- ✅ Orchestrator implemented
- ✅ Verification tests pass
- ✅ Documentation complete

### Integration (Next Sessions)

1. **Component 1:** Audio capture + Assembly AI
   - Will write to `meeting_transcript.txt`
   - Test orchestrator with live audio

2. **Component 3:** Agent prompt optimization
   - Test with real coding tasks
   - Iterate on system prompt
   - Ensure progress reporting works

3. **Component 4:** Progress watcher + TTS
   - Implement `bobby/progress_watcher.py`
   - Integrate real TTS (ElevenLabs or OpenAI)
   - Test voice output

### End-to-End Testing

1. Run all components simultaneously
2. Test with mock meeting (you speaking)
3. Test full flow: trigger → work → question → answer → complete
4. Debug integration issues
5. Dress rehearsal before real meeting

### Polish

1. Add logging to file (not just console)
2. Add configuration file (instead of constants)
3. Add metrics (triggers detected, agents launched, etc.)
4. Add health checks
5. Add restart mechanism

## Support

**Questions?**

1. Check this guide
2. Check `bobby/README.md`
3. Check `ARCHITECTURE.md` for full system design
4. Check `CLAUDE.md` for project overview

**Found a bug?**

1. Check "Troubleshooting" section above
2. Check orchestrator logs (console output)
3. Run verification tests: `python3 verify_orchestrator.py`
4. Test with demo: `./demo_orchestrator.sh`

**Want to modify?**

The orchestrator is designed to be readable and modifiable:

- Clear class structure
- Well-commented methods
- Configurable constants at top
- Verbose logging throughout

Feel free to adjust for your needs!

---

**The orchestrator is ready for integration with other Bobby components!**
