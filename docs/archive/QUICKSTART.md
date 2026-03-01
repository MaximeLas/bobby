# Bobby Orchestrator - Quick Start

## 30-Second Setup

```bash
cd /Users/maximelas/Projects/Unicorn

# Verify it works
python3 verify_orchestrator.py

# Run it
python3 bobby/orchestrator.py
```

## Basic Usage

### Terminal 1: Run Orchestrator
```bash
python3 bobby/orchestrator.py
```

### Terminal 2: Simulate Meeting
```bash
# Add meeting discussion
echo "[14:00:00] Max: We need a pricing page" >> meeting_transcript.txt
echo "[14:00:15] Michelle: Three tiers" >> meeting_transcript.txt

# Trigger Bobby
echo "[14:00:30] Max: Hey Bobby, please build this" >> meeting_transcript.txt
```

### Terminal 3: Watch Progress (Optional)
```bash
tail -f agent_progress.txt
```

## Triggers

### Launch Agent
```
"Hey Bobby, please build this"
```
→ Launches Claude Code with meeting context

### Resume Agent
```
"Thank you, Bobby"
```
→ Resumes Claude Code with answer to question

## Files

| File | Purpose |
|------|---------|
| `meeting_transcript.txt` | INPUT: Meeting transcript (you add lines here) |
| `agent_progress.txt` | OUTPUT: Agent writes progress here |
| `bobby/orchestrator.py` | Main orchestrator code |

## Testing

```bash
# Automated tests
python3 verify_orchestrator.py

# Interactive demo
./demo_orchestrator.sh

# Manual test
python3 test_orchestrator.py
```

## Common Commands

```bash
# Clear transcript
rm meeting_transcript.txt

# Watch orchestrator logs
python3 bobby/orchestrator.py | tee orchestrator.log

# Monitor progress
watch -n 1 tail agent_progress.txt

# Add test trigger
echo "[$(date +%H:%M:%S)] Max: Hey Bobby, please build this" >> meeting_transcript.txt
```

## Configuration

Edit `bobby/orchestrator.py`:

```python
DEBOUNCE_SECONDS = 30    # Ignore triggers within 30s
POLL_INTERVAL = 1        # Check file every 1s
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Trigger not detected | Check spelling, wait 30s for debounce |
| Claude not found | Install: Check Claude Code CLI |
| File not found | Create empty: `touch meeting_transcript.txt` |

## What's Next?

1. **Component 1:** Audio capture (writes to meeting_transcript.txt)
2. **Component 3:** Agent optimization (reads meeting context, executes tasks)
3. **Component 4:** Progress watcher (reads agent_progress.txt, speaks via TTS)

## Full Documentation

- **Complete guide:** ORCHESTRATOR_GUIDE.md
- **Implementation details:** IMPLEMENTATION_SUMMARY.md
- **System architecture:** ARCHITECTURE.md
- **Component docs:** bobby/README.md

---

**You're ready to go! 🚀**
