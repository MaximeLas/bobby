# Bobby - Build Progress Tracker

> **Note:** This is a historical build log from Oct 2025 when Bobby was first developed inside the `~/Projects/Unicorn` workspace. Some paths and status info are from that era. See `CLAUDE.md` in the project root for current state.

Track what's built, what's next, and blockers.

---

## Current Status

**Phase:** 🎯 Core System Working - Cleanup & Audio Setup Needed
**Last Updated:** 2025-10-27 (Session 2 - Audio + Voice Working!)
**Next Up:** Project cleanup, then finalize audio routing for Zoom

**🎉 MAJOR WIN:** Bobby responds to voice with acknowledgment and launches agents!

---

## Build Phases

### ✅ Phase 0: Planning (COMPLETE)

- [x] Define system architecture
- [x] Design component interactions
- [x] Choose technology stack
- [x] Create CLAUDE.md for project
- [x] Create ARCHITECTURE.md with detailed specs
- [x] Create PROGRESS.md (this file)

---

### ✅ Phase 0.5: Core Validation (COMPLETE) 🎉

**MAJOR MILESTONE:** Validated that agents can execute code from conversational meeting transcripts!

**What We Built:**

- [x] Test workspace (FlowTask - realistic SaaS landing page)
- [x] Realistic 12-minute meeting transcript (conversational, natural)
- [x] Orchestrator component (bobby/orchestrator.py) - fully tested
- [x] Ran Bobby agent with meeting transcript
- [x] **SUCCESS:** Bobby built complete pricing section from conversation!

**What We Proved:**

- ✅ Agents can understand conversational context (not formal specs)
- ✅ Agents can extract requirements from natural discussion
- ✅ Agents write proper progress updates to agent_progress.txt
- ✅ Orchestrator trigger detection works perfectly
- ✅ Session management (claude -p --continue) works
- ✅ Test environment approach is effective

**Test Results:**

- Bobby read 12-min conversation transcript
- Extracted: 3 pricing tiers, toggle, features, design requirements
- Created 4 new files (Pricing components + CSS)
- Modified Landing.jsx correctly
- NO BUILD ERRORS - compiled successfully
- All requirements met from conversational discussion

**Files Created:**

- test-workspace/ - FlowTask landing page
- test-workspace/meeting_transcript.txt - Realistic conversation
- bobby/orchestrator.py (358 lines, 6 tests passing)
- bobby/tts.py (placeholder)
- Comprehensive docs (ORCHESTRATOR_GUIDE.md, etc.)

**Commits:**

- Initial: FlowTask landing page before pricing
- After: Bobby's pricing section (387 additions, 6 files)

---

### ✅ Phase 1: Audio Capture & Transcription (WORKING!)

**Goal:** Meeting audio → `meeting_transcript.txt`

**Status:** ✅ WORKING with default microphone (needs Zoom setup)

**Completed:**

- [x] Install BlackHole audio device (via brew)
- [x] Set up Python environment (venv)
- [x] Install dependencies (pyaudio, assemblyai, python-dotenv)
- [x] Implement `test-workspace/bobby/audio_capture.py`
- [x] Test with live voice and `say` command
- [x] Orchestrator detects trigger from live audio
- [x] Real-time transcription works
- [x] Voice acknowledgment ("On it, building now")
- [x] Rename Bob → Bobby (better speech recognition)

**Still TODO:**

- [ ] Configure Audio MIDI Setup for Zoom (Aggregate Device)
- [ ] Test with actual Zoom meeting
- [ ] Verify multi-speaker transcription in Zoom

**Estimated Time:** 3-4 hours
**Started:** 2025-10-25

**Resources:**

- Assembly AI docs at: /Users/maximelas/Projects/Unicorn/assemblyai/
- PYTHON_SDK_GUIDE.md has latest API info
- Max has Assembly AI credits

**Testing Plan:**

- Use existing test-workspace/meeting_transcript.txt (stop before trigger)
- Speak "Hey Bobby, please build this" with live mic
- Verify it appends to transcript
- Verify orchestrator detects and launches agent

**Notes:**

- Max has Assembly AI credits and experience with it
- BlackHole is free and easy to install on macOS

---

### ✅ Phase 2: Code Execution Agent (VALIDATED!)

**Goal:** Agent can execute tasks and write progress

**Status:** ✅ COMPLETE - Core functionality proven!

**What We Tested:**

- [x] Created realistic meeting transcript (12 min conversation)
- [x] Ran agent with: `claude -p [system prompt]`
- [x] Agent read conversational transcript successfully
- [x] Agent extracted requirements correctly
- [x] Agent built complete pricing section (4 files, 387 lines)
- [x] Agent wrote perfect progress updates to agent_progress.txt
- [x] Agent integrated feature into existing codebase
- [x] NO BUILD ERRORS - feature works on localhost
- [x] Verified deployment (Vite hot-reload worked)

**System Prompt Used:** (see test command in session)

- Minimal, clear instructions
- Reference to @meeting_transcript.txt
- Progress format specified
- Emphasis on extracting from conversational context

**Results:**

- ✅ Built Pricing.jsx with monthly/annual toggle
- ✅ Built PricingCard.jsx component
- ✅ Created matching CSS files
- ✅ Integrated into Landing.jsx correctly
- ✅ All requirements from 12-min conversation met
- ✅ Professional code quality
- ✅ Design system consistency maintained

**Time:** ~2-3 minutes of agent execution

**Key Learning:**

- Agents CAN understand conversational context
- Don't need formal specs - natural discussion works
- Progress reporting format works perfectly
- Simple system prompt is sufficient

---

### ✅ Phase 3: Trigger Detection & Orchestration (COMPLETE!)

**Goal:** Detect "Hey Bobby", launch/resume agent

**Status:** ✅ COMPLETE - Agent 2 built this perfectly!

**Completed:**

- [x] Implemented `bobby/orchestrator.py` (358 lines)
- [x] Implemented transcript file watcher (1-second polling)
- [x] Implemented trigger detection ("Hey Bobby, please build this")
- [x] Implemented answer extraction ("Thank you, Bobby")
- [x] Tested launch flow manually
- [x] Added 30-second debouncing
- [x] Added comprehensive error handling
- [x] Created full test suite (6 tests - all passing)

**Deliverables:**

- bobby/orchestrator.py - Main orchestrator class
- bobby/tts.py - TTS placeholder (ready for ElevenLabs)
- verify_orchestrator.py - Automated tests (6/6 passing)
- test_orchestrator.py - Interactive test suite
- demo_orchestrator.sh - Demo walkthrough
- ORCHESTRATOR_GUIDE.md - Complete documentation
- QUICKSTART.md - Quick reference

**Features:**

- File watching with position tracking
- Trigger detection (case-insensitive, multiple variants)
- Context extraction (last 15 lines)
- Answer extraction (smart parsing)
- Claude Code session management (launch/resume)
- speak_bob() placeholder (ready for TTS integration)
- Verbose logging
- Graceful error handling

**Time:** ~1.5 hours (Agent 2 built this)

**Tests:** All passing ✅

```bash
python3 verify_orchestrator.py
# 6/6 tests passed
```

---

### ⏳ Phase 4: Progress Watcher & Voice Output

**Goal:** Bobby speaks questions and completions

**Tasks:**

- [ ] Implement `bobby/progress_watcher.py`
- [ ] Implement progress file watcher
- [ ] Implement `bobby/tts.py` (ElevenLabs)
- [ ] Test TTS with sample text
- [ ] Choose Bobby's voice (Adam, Antoni, Josh?)
- [ ] Test progress display (console output)
- [ ] Test Bobby speaking questions
- [ ] Test Bobby speaking completions
- [ ] Test Bobby speaking errors
- [ ] Add fallback (if TTS fails, print to console)

**Estimated Time:** 2-3 hours
**Actual Time:** _TBD_

**Blockers:**

- Need ElevenLabs API key
- Depends on Phase 2 (progress file format)

---

### ⏳ Phase 5: Integration & Testing

**Goal:** All components work together

**Tasks:**

- [ ] Set up multi-terminal workflow (3 scripts running)
- [ ] Test Component 1 + 2 (audio → trigger)
- [ ] Test Component 3 + 4 (agent → progress → voice)
- [ ] Run full end-to-end test (just Max)
- [ ] Debug issues
- [ ] Add logging (verbose output for debugging)
- [ ] Test error scenarios (bad audio, failed agent, etc.)
- [ ] Optimize trigger sensitivity
- [ ] Add startup script (launch all components)

**Estimated Time:** 4-6 hours
**Actual Time:** _TBD_

**Blockers:**

- Depends on all previous phases

---

### ⏳ Phase 6: Polish & Demo

**Goal:** Ready for Kevin & Michelle demo

**Tasks:**

- [ ] Dress rehearsal (full meeting simulation)
- [ ] Fix any bugs found in rehearsal
- [ ] Prepare demo script (what to say)
- [ ] Test with simple task (high success probability)
- [ ] **DEMO DAY!** 🎉
- [ ] Gather feedback from Kevin & Michelle
- [ ] Document lessons learned

**Estimated Time:** 2-4 hours
**Actual Time:** _TBD_

**Blockers:**

- Need working system (Phase 5 complete)
- Need to schedule meeting with Kevin & Michelle

---

## Component Checklist

| Component        | Status         | Files                             | Notes                    |
| ---------------- | -------------- | --------------------------------- | ------------------------ |
| Audio Capture    | ⏳ Not Started | `bobby/audio_capture.py`          | BlackHole setup required |
| Orchestrator     | ⏳ Not Started | `bobby/orchestrator.py`           | Core logic               |
| Agent Execution  | ⏳ Not Started | System prompt (in initial prompt) | Iterative refinement     |
| Progress Watcher | ⏳ Not Started | `bobby/progress_watcher.py`       | File watcher             |
| TTS              | ⏳ Not Started | `bobby/tts.py`                    | ElevenLabs integration   |
| Utils            | ⏳ Not Started | `bobby/utils.py`                  | Shared helpers           |

**Legend:**

- ✅ Complete
- 🔄 In Progress
- ⏳ Not Started
- ❌ Blocked

---

## Decisions Made

| Decision                | Choice                            | Rationale                                      |
| ----------------------- | --------------------------------- | ---------------------------------------------- |
| Meeting Platform (MVP)  | Local mic/speakers                | Faster than Zoom SDK, works with existing Zoom |
| Speech-to-Text          | Assembly AI                       | Max has credits, good quality, speaker labels  |
| Text-to-Speech          | ElevenLabs                        | Natural voice, worth the cost                  |
| Code Execution          | Claude Code CLI                   | Native integration, workspace access           |
| Trigger Phrase (Launch) | "Hey Bobby, please build this"    | Clear intent, avoids ambiguity                 |
| Trigger Phrase (Answer) | "Thank you, Bobby"                | Natural in conversation                        |
| Session Management      | `claude -p --continue`            | Simple, no session ID tracking needed          |
| Deployment (MVP)        | Localhost + Vite hot reload       | Fastest, can upgrade to Vercel later           |
| Progress Updates        | File-based (`agent_progress.txt`) | Simple, debuggable, extensible                 |
| Voice for Bobby         | TBD (test in Phase 4)             | Will choose between Adam, Antoni, Josh         |

---

## Blockers & Risks

### Current Blockers

_None yet - still in planning phase_

### Known Risks

| Risk                      | Severity  | Mitigation                                              |
| ------------------------- | --------- | ------------------------------------------------------- |
| Agent breaks build        | 🟡 Medium | Deploy to localhost only, not production                |
| Agent misunderstands task | 🟡 Medium | Comprehensive system prompt, test with mock transcripts |
| Audio quality issues      | 🟢 Low    | Test in real meeting, adjust trigger sensitivity        |
| Triggers fire incorrectly | 🟢 Low    | Debounce (30s cooldown), specific trigger phrases       |
| Long tasks (>5 min)       | 🟢 Low    | Progress updates keep people engaged                    |
| Cost concerns             | 🟢 Low    | Estimate $2-5/meeting, acceptable for MVP               |
| `--continue` breaks       | 🟡 Medium | Don't run other Claude commands during meeting          |

---

## Testing Checkpoints

### Checkpoint 1: Component Tests (After Phase 1-4)

- [ ] Audio capture produces quality transcript
- [ ] Agent executes simple task successfully
- [ ] Triggers detect correctly
- [ ] Progress updates appear in real-time
- [ ] Bobby's voice sounds natural

### Checkpoint 2: Integration Test (After Phase 5)

- [ ] Full flow works: audio → trigger → agent → voice
- [ ] No manual intervention needed (besides triggers)
- [ ] Total time <5 minutes for simple task

### Checkpoint 3: Demo Rehearsal (Before Phase 6)

- [ ] Can complete demo task reliably
- [ ] Kevin & Michelle will understand what's happening
- [ ] Surprise factor intact (Bobby not visible initially)

---

## Lessons Learned

_Will be filled in as we build..._

### What Worked Well

- TBD

### What Was Harder Than Expected

- TBD

### What We'd Do Differently

- TBD

---

## Future Enhancements (Post-MVP)

**Nice to Have (v1.1):**

- [ ] Discord migration (Bobby as real participant)
- [ ] Progress updates in Discord chat
- [ ] Vercel preview deployments
- [ ] Avatar/logo for Bobby
- [ ] Better error messages

**Ambitious (v2.0):**

- [ ] Multiple specialized Bobs (design, backend, testing)
- [ ] Proactive suggestions ("Should I build this?")
- [ ] Natural interruption (no triggers)
- [ ] Meeting summaries & action items
- [ ] Integration with Linear, Notion, Figma

---

## Quick Reference

### Start All Components

```bash
# Terminal 1: Audio capture
python bobby/audio_capture.py

# Terminal 2: Orchestrator
python bobby/orchestrator.py

# Terminal 3: Progress watcher
python bobby/progress_watcher.py
```

### Test Individual Components

```bash
# Test audio capture
python bobby/audio_capture.py

# Test agent (manual)
claude -p "You are Bobby... [prompt]"

# Test progress watcher
echo "QUESTION: Test question?" >> agent_progress.txt
python bobby/progress_watcher.py

# Test TTS
python -c "from bobby.tts import speak; speak('Hello from Bobby')"
```

### Useful Commands

```bash
# View live transcript
tail -f meeting_transcript.txt

# View live progress
tail -f agent_progress.txt

# Clear files (reset)
> meeting_transcript.txt
> agent_progress.txt
```

---

## Notes

- Max is building a startup MVP (separate project), so Bobby is a side project
- Goal is to be effective and structured, not rush
- Future agents should be accountable co-founders, not just tools
- This document should be updated as we build

---

**Let's build something amazing! 🚀**

_Last updated: 2025-10-25_
