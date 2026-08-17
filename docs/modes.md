# Bobby's operating modes — the map

_Written 17 Aug 2026 (demo-week session), distilled from two independent design
brainstorms plus session synthesis, after Max asked: "what are the different modes we
actually have, and is the obvious framing even right?" It wasn't, quite. This page is
a naming layer — nothing in it changes runtime behavior._

## The core split: stance vs rig

The old framing ("local mode / Discord mode / sidecar mode") mixes two unrelated
things. What a mode IS socially, and how it's WIRED mechanically, vary independently:

- **Stance** — the social contract of a session. This is what deserves the word "mode".
- **Rig** — the plumbing underneath. Swappable per meeting; carries no social meaning.

The tell that the old framing was wrong: "local" and "Discord" are the *same stance*
on two rigs (which is why every capability had to be built twice and PR #3 shipped a
"voice parity" chore), while the Steven-call sidecar — which ran on *local's* rig —
is a genuinely different thing.

## Stance: four dials

| Dial | Values | The question it answers |
|---|---|---|
| **Principal** | `room` · `operator` | Who does Bobby serve — everyone present, or Max privately? |
| **Disclosure** | `announced` · `disclosed` · `covert` | What do the other participants know? |
| **Authority** | `capture` < `advise` < `speak` < `act` | The most privileged thing Bobby may do (a ladder — each level implies those below) |
| **Initiative** | `pull` · `nudge` · `push` | Who starts a Bobby turn: summoned only, cheap-channel volunteering, or taking the floor |

Combinations are constrained, not free: `speak` implies `announced` (speaking IS
disclosing); `operator` implies output lands only where Max perceives it; `covert`
must hard-forbid any surface that republishes the other party's words off this
machine (that one is a legal boundary, not a style choice).

## Rig: four layers

| Layer | Options today |
|---|---|
| **Capture** | room mic (mixed voices) · per-speaker Discord channels · replayed recording (`tools/replay_stream.py`) |
| **Pipeline** | finals-only (wake-word-safe, 5–15s) · partials + diarization + event log (`BOBBY_SIDECAR=1`, ~1–2s live line) |
| **Cognition** | brain (`bobby/brain.py`, quip-speed) · coding agent (`agent_runner`) · an external Claude session reading the transcript (the most capable Bobby ever run) |
| **Surface** | room speakers · Discord voice/embeds · files + terminal (silent) |

Naming correction that matters: **"sidecar" today names a pipeline, not a stance.**
`BOBBY_SIDECAR=1` turns on partials/diarization/event-log; what made the Steven call
*silent* was launching capture alone — nothing with a mouth. Keeping those ideas
fused would make "partials-based trigger detection" (the top post-demo item) sound
like a contradiction when it's just: sidecar *pipeline* under participant *stance*.

## What exists, in these terms

| Preset | Stance (principal / disclosure / authority / initiative) | Rig notes |
|---|---|---|
| **Participant** | room / announced / act / pull | The demo. One stance, two rigs (local, Discord) |
| **Colleague** | room / announced / act / **push** | `BOBBY_PROACTIVE=1` (gate-heavy, off by default) |
| **Scribe** | either / disclosed / **capture** / — | `BOBBY_SIDECAR=1` alone; cannot make a sound |
| **Second** | operator / covert-or-disclosed / **advise** / pull | The 4 Aug Steven call: Scribe rig + external session + Max's typed 3–5-word hints (measured better than transcript reads) |

## What the map predicts (gaps worth building toward)

- **The Whisperer** (operator / nudge): private one-line nudges to Max's screen —
  socially free (takes no floor), and the sidecar design doc's open question #1 is
  exactly whether to allow it. Blocked only by proactive's current welding of
  "volunteer" to "speak aloud".
- **Public + private simultaneously**: Participant for the room and Second for Max on
  the same meeting. Conceptually two consumers of one event log (v2 already built
  that); structurally blocked because `BOBBY_WORKSPACE` does two jobs — *where
  runtime artifacts live* and *which repo the agent may mutate*. The config file
  should split `session_dir` from `repo` (and `repo` unset ⇒ authority capped at
  `advise`, structurally).
- **Post-meeting Bobby** (push + act, async): "build the three things we agreed."
  The cell that is most dangerous live is the *safest* asynchronously — no floor to
  steal, complete transcript. Arguably ships before in-meeting proactive.
- **Per-speaker authority**: today any voice in mic range can say five words and
  launch an unsandboxed agent. Fine among friends (David triggering Bobby is the
  demo); the moment Bobby leaves friendly rooms this becomes a `may_act = ["Max"]`
  config field — enforceable only on rigs that resolve identity (Discord natively;
  room mic via the new speaker-labels flag + name mapping).

## Where this lands in config

The planned per-workspace Bobby config file (design anchor in `docs/NEXT.md`) is the
natural home: a stance **preset** plus rig fields plus `may_act`, MCP/tool selection,
model, and dev URL. Presets are the interface; dials are the semantics; illegal
combinations get refused at startup rather than documented.
