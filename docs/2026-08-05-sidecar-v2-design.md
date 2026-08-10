# Sidecar v2 — design

_Written 2026-08-05 (overnight), from the measured findings of Bobby's first real-world use (4 Aug Steven call) and the same-audio replay experiment. Evidence: meetings repo `docs/experiments/2026-08-04-realtime-streaming-vs-batch.md` and `…/2026-08-05-streaming-replay-partials-diarization.md`._

_**Status 2026-08-11: IMPLEMENTED** — `bobby/sidecar.py` + `BOBBY_SIDECAR=1` in `audio_capture.py`, tested offline against the recorded 4 Aug event logs (`tests/test_sidecar.py`, 7 tests). Launcher: max-os `steven/sidecar-transcribe.sh`. One addition beyond this doc: the writer bootstraps its state from `events.jsonl` on startup, so the restart loop can't wipe the derived transcript. ⚠️ The live-endpoint check (`tools/replay_stream.py --sidecar-dir`) is BLOCKED on AssemblyAI account credit ("Insufficient funds", 11 Aug) — top up, rerun it, and only then trust the pipeline for a real call._

## What changed in our understanding

Four measured facts drive this design (all verified on the actual call audio, not assumed):

1. **Partial turns stream by default** at ~1.3 s cadence, even mid-monologue. The live call's 60-second blackouts existed because `streaming.should_write_turn` discards non-final turns — a wake-word safety rule applied in a mode with no wake word. The information was always arriving.
2. **Diarization works**: `speaker_labels=True, max_speakers=N` gives ~99% word-level speaker accuracy on real two-person call audio, with a `SpeakerRevisionEvent` (observed: once, at session end) that retroactively relabels earlier turns — so the writer must be able to *amend*, not just append.
3. **With the new flags, finalized turns arrive every ~10 s (max 45 s)** instead of 60-second walls, and seam duplication drops below batch level.
4. **Overlapped interjections — the one thing the transcript structurally lost — usually appear in partials and are then erased by the turn-commit.** ("No one watches the fucking stream." sat verbatim in a partial; its final kept none of it.) A partial-vs-final diff is a free overlap-recovery channel.

## Design principles

- **The event log is the source of truth; the transcript is a derived view.** Today's `meeting_transcript.txt` conflates capture and presentation, which made every question about the 4 Aug call forensic. v2 writes machine-readable events first and renders text from them.
- **Mode separation, not mode entanglement.** Wake-word paths (local orchestrator, Discord) keep today's finals-only gate and behavior, byte-for-byte. Sidecar mode gets the new pipeline. No shared-code change may alter trigger semantics.
- **Typed hints are the product's primary input channel; the transcript is background context.** Measured in the field: 3–5-word typed hints beat transcript reads on both latency and intent. The transcript's job is to be *fresh enough* that the assistant is never blind — not to be the interface.

## Architecture

```
mic/BlackHole → audio_capture (sidecar mode)
                   ├── events.jsonl        (append-only: every TurnEvent, SpeakerRevision,
                   │                        Begin/Termination/Error — full payload, wall+audio time)
                   └── meeting_transcript.txt  (DERIVED: atomically rewritten from the turn store
                                                on every final, revision, and partial tick)
```

### Streaming config (sidecar mode only)

```python
StreamingParameters(
    sample_rate=16000,
    speech_model="universal-3-5-pro",
    speaker_labels=True,
    max_speakers=int(os.environ.get("BOBBY_MAX_SPEAKERS", "2")),
    include_partial_turns=True,
    continuous_partials=True,
    prompt=STREAMING_PROMPT,          # existing env override
    keyterms_prompt=STREAMING_KEYTERMS,
)
```

Mode selection: `BOBBY_SIDECAR=1` env var (consistent with the existing `BOBBY_*` overrides; `call2-transcribe.sh`-style launchers set it). Default off → current behavior everywhere.

### The turn store + renderer

In-memory `dict[session_id, turn_order] → {words, label, text, final?}` fed by events; on change, rewrite the transcript via temp-file + `os.replace` (a 60-min call renders to <100 KB; consumers using `tail -n 20` are unaffected by rewrites). Render format:

```
[15:14:35] [A] Yeah, it is the marketing, it's the distribution, …
[15:14:44] [B~] No one watches the fucking stream.        ← overlap-recovered line
[15:14:45] [A] It's a clip factory. So like we would generate …
⋯ [A] and the thing I keep coming back to is            ← live partial, always last line
```

- **Live partial line (`⋯`)**: the current in-flight turn's latest partial, rewritten in place. This alone converts the 60 s blackout into ~1–2 s of lag.
- **Overlap recovery (`[X~]`)**: at each final commit, diff the last partial's words against the final's words; a dropped run (proposed threshold: ≥3 consecutive words, or ≥2 ending in sentence punctuation — **tune against the preserved replay JSONLs**, which contain labeled ground-truth cases) is emitted as its own line, attributed by per-word speaker if available, marked `~` as uncertain.
- **Amendment on `SpeakerRevision`**: update store, re-render. Optionally keep a `# revised: turn N A→B` trailer line so a human notices, since the event log has the full provenance anyway.
- **Speaker naming**: raw A/B in the event log forever (provenance); an optional mapping applied at render time from `BOBBY_SPEAKER_NAMES="A=Max,B=Steven"` *or* a live-editable `speaker_names.txt` in the workspace, so the in-call assistant (or Max) can set the mapping after the first exchange. Names stay OUT of the streaming prompt — the 4 Aug lesson stands: prompt-induced `[Speaker:Name]` tags were hallucinations; real labels come from diarization and get named client-side.
- **Session restarts** (the wrapper's restart loop stays — AAI sessions still die silently): `turn_order` resets per session, so the store keys by `(session_id, turn_order)`; the renderer just concatenates sessions.

### events.jsonl record shape

One JSON object per websocket event, same shape the replay harness writes: `{wall, audio_sec, type, data}` with `data` = the SDK model dump (turn_order, end_of_turn, transcript, words[] with start/end/confidence/speaker/word_is_final, end_of_turn_confidence, speaker_label, …). This is the file every future investigation reads instead of reverse-engineering timestamp gaps — and the 4 Aug clean showed the sidecar's logs have a second life as attribution evidence, which argues for logging more, not less.

### What does NOT change

- `streaming.should_write_turn` and both wake-word modes (local orchestrator, Discord). Trigger detection stays finals-only — partials mid-word firing a build trigger is still a real risk, and that guard was always correct *for that mode*.
- File-based IPC as the integration surface. `meeting_transcript.txt` keeps its name and `[HH:MM:SS]` line shape (now with `[A]`-style labels), so existing consumers keep working.
- The restart-loop launcher pattern.

## Testing (the replay harness makes this deterministic)

`tools/replay_stream.py` (tonight's experiment harness, promoted into the repo) streams any audio file through the real endpoint at 1×..N× pace; `tools/analyze_replay.py` computes gap histograms, label concordance vs a batch transcript, and loss checks. Test plan:

1. Unit: turn store + renderer against a recorded `events.jsonl` (no network, fully deterministic — replay the preserved 4 Aug logs).
2. Integration: replay a 3-min slice of the 4 Aug `.m4a`; assert no inter-line gap >15 s in the derived transcript, and that the known interjection cases produce `[X~]` lines.
3. Live: next real call runs sidecar v2 with the phone recording in parallel, then re-runs the 3-way diff (n=1 → n=2).

## Consequences for the in-call assistant prompt (product layer)

The next call's sidecar prompt should state the *new* transcript physics instead of the old guesses: last line is live within ~1–2 s; finalized lines land every ~10 s; speaker labels are real and ~99% but the `~` lines are uncertain; earlier lines can be amended. The prompt's shorthand system (typed hints first, `?`, `line`, `gaps`) survives unchanged — it was the best-performing part of v1.

## Open questions for Max (none block implementation)

1. **Attention contract** (the meta-question): should the sidecar ever push (e.g. surface an overlap-recovered pushback line proactively), or stay strictly pull? This decides a default, not the architecture — v2 as designed is strictly pull.
2. Overlap-line threshold: tune conservative (miss some) or eager (some noise)? Proposal: conservative in the transcript, eager in the event log.
3. Should Discord mode eventually write `events.jsonl` too (it already has per-user attribution via separate sessions)? Cheap, but out of scope here.

## Implementation order (one session of work)

1. Event logger + `BOBBY_SIDECAR` config switch (no behavior change elsewhere).
2. Turn store + derived-transcript renderer (finals only) + amend-on-revision.
3. Live partial line.
4. Overlap-recovery diff, threshold tuned on the replay JSONLs.
5. Replay-based tests; update `docs/NEXT.md` and the sidecar launcher template.
