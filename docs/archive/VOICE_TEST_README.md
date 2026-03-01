# Bobby Voice Test Mode

## Quick Start

Test Bobby's Eastern European voice **without launching agents** (saves credits!):

```bash
./test_bobby_voice_only.sh
```

To stop:
```bash
./stop_bobby_test.sh
```

---

## What Gets Tested

### ✅ Tested:
- Trigger detection ("Hey Bobby, please build this")
- Bobby's Eastern European voice response via ElevenLabs
- Transcription pause/resume (prevents echo)
- Audio capture from microphone

### ❌ NOT Tested:
- Claude Code agent execution
- Actual code changes
- API credits usage for agent

---

## How to Use

1. **Run the test script:**
   ```bash
   ./test_bobby_voice_only.sh
   ```

2. **Wait for it to start** (takes a few seconds)

3. **Say into your microphone:**
   > "Hey Bobby, please build this"

4. **Bobby will respond with voice:**
   > "On it, building now"

   (In his Eastern European accent!)

5. **Test complete!** Bobby won't launch an agent in test mode.

6. **Stop the test:**
   ```bash
   ./stop_bobby_test.sh
   ```
   Or press `Ctrl+C` in the terminal

---

## Tmux Layout

The test script opens 2 windows in tmux:

1. **orchestrator** - Watches transcript for triggers (test mode)
2. **audio** - Captures your microphone audio

To switch between windows in tmux:
- `Ctrl+B` then `n` (next window)
- `Ctrl+B` then `p` (previous window)

---

## Troubleshooting

### Bobby doesn't respond:
- Check that your microphone is working
- Make sure you said the exact trigger: "Hey Bobby, please build this"
- Wait 2-3 seconds for Assembly AI to transcribe

### No audio output:
- Check your speaker volume
- Verify `ELEVENLABS_API_KEY` is set in your environment
- Check the orchestrator window for error messages

### Can't stop the test:
```bash
tmux kill-session -t bobby-test
```

---

## Full Production Mode

Once voice test works, run the full system:

```bash
./start_bobby.sh
```

This will:
- ✅ All the voice testing features
- ✅ Launch Claude Code agents
- ✅ Execute code changes
- ✅ Show progress updates

---

## File Structure

```
bobby/
├── orchestrator.py              # Production orchestrator (launches agents)
├── orchestrator_test_voice.py   # Test orchestrator (voice only)
└── tts.py                       # ElevenLabs TTS with Eastern European voice

Scripts:
├── test_bobby_voice_only.sh     # Test voice without agents
├── stop_bobby_test.sh           # Stop voice test
├── start_bobby.sh               # Full production mode
└── stop_bobby.sh                # Stop production mode
```

---

## Next Steps

After successful voice test:
1. Test full system with `./start_bobby.sh`
2. Try a simple task: "Hey Bobby, please build this. Add a welcome message."
3. Watch Bobby build in real-time!
