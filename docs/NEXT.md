# Bobby — Where Things Stand & What's Next

_Written 2026-07-12, at the end of the July revival sprint; updated later
the same day after the backlog sprint (PR #3). This is the handoff doc:
everything here is executable by any capable agent (or Max) without
additional context. Read this first when picking Bobby back up._

## Current state

- **PR #1 (`revival/universal-3-5-pro`)** — the revival: Universal-3.5 Pro
  Realtime, DAVE-era py-cord 2.8, stoppable agent, `/bobby resume|stop`,
  fresh-eyes review applied. **Open, awaiting Max's checklist + merge.**
- **PR #2 (`feature/conversational-bobby`, stacked on #1)** — Bobby answers
  "Hey Bobby, <anything>" with a spoken, transcript-grounded reply
  (`bobby/brain.py`). **Draft: code + offline tests done; needs Max's live
  verification.**
- **PR #3 (`claude/bobby-capabilities-av0r9h`, stacked on #2)** — the
  backlog sprint: dev-URL config, brain API fast path, local-mode voice
  parity, and flag-gated proactive suggestions (all four detailed in the
  backlog below). **Draft: offline-verified; nothing in it touches the
  AAI/Discord/DAVE surface, so no new live checklist items beyond #1/#2's.**
- Offline suite: `uv run python3 tests/run_tests.py` — 90 tests, no keys needed.
- ElevenLabs plan lapsed → voice output falls back to macOS `say` (works,
  verified). Borat voice returns if the plan (~$5/mo) is renewed.
- `sandbox/` has uncommitted March demo residue (`/hello` page + router) —
  Max to decide: keep or revert. Runtime files there are gitignored.
- **(Added 5 Aug)** First real-world use happened (4 Aug, sidecar mode) and was
  measured end-to-end. Sidecar v2 is designed from those measurements:
  `docs/2026-08-05-sidecar-v2-design.md` (partials + diarization + event-log
  architecture; replay test harness in `tools/`).
- **(11 Aug)** Sidecar v2 IMPLEMENTED: `bobby/sidecar.py`, `BOBBY_SIDECAR=1`
  switch, 7 offline tests replaying recorded real-call events
  (`tests/test_sidecar.py`). Wake-word paths untouched. Launcher for the next
  call: max-os `steven/sidecar-transcribe.sh`. ⚠️ AAI "Insufficient funds" (11 Aug) —
  RESOLVED 17 Aug (account was funded all along; `.env` held a stale key from the old
  account). The v2 live check is still pending — rerun it:
  `uv run python tools/replay_stream.py <audio.m4a> --out /tmp/ev.jsonl
  --start 2280 --duration 120 --speaker-labels --max-speakers 2 --partials
  --continuous-partials --sidecar-dir /tmp/sidecar-check`.

## (17 Aug) Demo-week state & decisions

- **Keys:** AAI funded + key synced into `.env` (streaming token 200). ElevenLabs
  re-subscribed (Starter, monthly); new restricted key `bobby-local` (TTS + STT + STS +
  User + Voices-read) in `.env`. ⚠️ Two silent key failures in one day, same root cause:
  `load_dotenv()` does not override shell exports, so a stale `~/.zshrc` copy shadows
  `.env` (and vice versa when `.env` is the stale one). Rule going forward: **`.env` is
  canonical.** Note (17 Aug evening): Max keeps a copy of the EL key in `.zshrc` too —
  same key everywhere is harmless, but on any future rotation BOTH copies must be
  updated, or the shell copy silently shadows `.env` again. Second trap: ElevenLabs' Create-Key
  dialog shows "Unlimited" as a *placeholder* in the credit-limit field, but leaving it
  untouched can mint a key with quota 0 → `quota_exceeded` on first use.
- **Decisions:** David demo = LOCAL mode, in person (Discord mode right after, once
  local goes smoothly — the DAVE go/no-go moves to that week). Brain stays on the
  `claude` CLI (Max's plan, $0 marginal); PR #3's direct-API path stays dormant unless
  `ANTHROPIC_API_KEY` is set.
- **Before the demo:** add `tools/preflight.py` — a 2-second live check to run before
  every session/demo. Design constraints (learned 17 Aug): the EL check MUST be an
  actual tiny TTS generation — `/v1/user/subscription` reports healthy even when the
  key's own quota is 0, so it cannot catch the quota trap; and don't probe `/v1/models`
  (the `bobby-local` key deliberately lacks `models_read`). AAI check = streaming token
  request. Consider `load_dotenv(override=True)` too, but first confirm no `BOBBY_*`
  launch-time overrides collide with `.env` contents.
- **Before the demo (small code fix):** port `discord_bot._speak_in_voice`'s clean EL
  error unwrapping (`e.body['detail']['message']`) into `tts.speak()` — tts.py currently
  dumps raw HTTP headers on failure, burying the cause, and local mode (the demo path)
  is exactly where we'd be debugging live.

## Post-demo backlog additions (17 Aug)

- **Partials-based trigger detection** — the wake-word path still waits for finalized
  turns (5–15s lag); sidecar v2 already consumes ~1.3s partials. Highest-leverage
  latency win, no new vendor. After the David demo, not before.
- **Second transcription engine (ElevenLabs Scribe v2 Realtime)** — $0.39/hr, ~150ms
  model latency, behind a config flag. Half latency experiment, half redundancy: the
  AAI funding outage left Bobby with zero transcription; a second engine is cheap
  insurance.
- **ElevenLabs SDK upgrade** — audited 17 Aug by byte-level sdist diff (2.54.0 pinned vs
  2.64.0 latest): Bobby's entire call surface is byte-identical, `eleven_flash_v2_5`
  still current (turbo/monolingual retired, not flash), the Borat voice ID verified live
  in My Voices. **Scribe v2 Realtime (incl. keyterms) and Speech-to-Speech are already
  in pinned 2.54.0** — no upgrade needed to prototype either. Upgrade post-demo at
  leisure; 2.64.0 adds Scribe extras (`filter_background_audio` is the interesting one
  for meeting audio) and renames one STS type we don't import.
- **Fix stale docs/ARCHITECTURE.md §ElevenLabs (~lines 544–558)** — shows the pre-2.x
  API (`from elevenlabs import generate, play, set_api_key` + a model removed Jul 2026);
  a future agent following it would write broken code.
- **Speech-to-Speech experiments** — the `bobby-local` key already has STS access
  (e.g. voice-convert a speaker into Bobby's voice live; demo garnish, low priority).
- **Custom cloned Bobby voice / voice refresh** — Starter includes Instant Voice
  Cloning; the current Borat voice ("Valentin", `lIaJUjvN2nyLPU9wRIa0`) is a library
  preset we don't own, picked ~Nov 2025. Two options worth a browse someday: newer
  library voices closer to actual Borat, or cloning our own (removes the third-party
  dependency). Max's call: nice-to-have, not demo-critical. (17 Aug)
- **ElevenAgents (full-duplex conversational Bobby)** — a real architectural rewrite on
  a separate EL product/plan. Parked, named, not scoped.

## Max's pre-merge checklist (~25 min, in order)

1. `.env`: set `ASSEMBLYAI_API_KEY` to the working key (the one in `.zshrc`).
   The committed code never sees your key; `.env` is gitignored.
2. `uv run python3 tests/manual/test_agent_loop.py` — proves
   transcript → trigger → real agent → build. Expect a "Night Shift" page
   in the sandbox app.
3. `uv run python3 tests/manual/test_brain.py` — one live conversational
   answer (~30s). Checks CLI auth + answer quality/character.
4. Discord live (the **DAVE go/no-go**): `uv run python start_discord.py`,
   join the voice channel, speak → `[Max]` lines must appear in
   `sandbox/meeting_transcript.txt`. Then: say the build trigger, try
   `/bobby stop` mid-build, and say "Hey Bobby, how is it going?" (tests
   the brain in-call, mid-build).
5. Merge PR #1, then PR #2.

If step 4 shows NO transcript lines: Pycord 2.8 voice receive is broken
under DAVE → check github.com/Pycord-Development/pycord issues; fallback
plan is BlackHole → Zoom/Meet capture (not yet built, see backlog).

## The David demo runbook

Principle: **spontaneous about WHAT, bounded on SCOPE** (small / visual /
additive / self-contained — one agent run). `/bobby build <task>` is the
typed fallback if a voice trigger mis-hears; `/bobby stop` aborts a bad run.

1. **Rehearse solo on sandbox** (any small feature; do the full voice loop).
2. **Rehearse solo on Publico** via a throwaway worktree so `main` is
   structurally untouchable:
   ```bash
   cd ~/Projects/publico-app
   git worktree add ../publico-demo -b bobby-demo
   cd ../publico-demo && npm install && npm run dev   # note the port
   BOBBY_WORKSPACE=~/Projects/publico-demo BOBBY_DEV_URL=http://localhost:3000 \
     uv run python start_discord.py
   ```
   (`BOBBY_DEV_URL` sets the dev-server URL the agent deploys to and
   announces — defaults to Vite's 5173 for the sandbox.)
3. **Back-pocket features** (from the David call, 26 Jun): (a) hero page
   upgrade — David: "just whatever, very basic" = safest; (b) drafting-window
   source footnotes — David explicitly wants it; bigger, rehearse first.
4. Go live with David only after 1-2 land clean.

## Backlog (each item self-contained enough to hand to an agent)

- ~~**Local-mode converse + completion voice parity.**~~ **DONE (PR #3).**
  New shared helper `bobby/voice.py` (pause flag + self-speech filtering);
  orchestrator got the converse route + spoken resume ack; progress
  watcher speaks QUESTION/COMPLETE/ERROR (`--no-voice` to disable). Known
  limitation: local converse only answers while idle — launch_agent
  blocks the local watch loop, unlike Discord.
- ~~**Brain latency v2.**~~ **DONE (PR #3).** `_run_llm()` dispatches to
  the Anthropic API (~1-3s, `claude-haiku-4-5`) when `ANTHROPIC_API_KEY`
  is set and `uv sync --extra brain` is installed; any API failure falls
  back to the CLI. Zero config keeps the old CLI-only behavior.
- ~~**Prompt URL.**~~ **DONE (PR #3).** `BOBBY_DEV_URL` env var →
  `config.DEV_SERVER_URL` (default Vite 5173). For the Publico worktree
  in the runbook above, add `BOBBY_DEV_URL=http://localhost:3000` to the
  start command.
- **NEW — Proactive suggestions (PR #3; needs live rehearsal before any
  demo).** `BOBBY_PROACTIVE=1` makes Bobby offer to build features he
  hears discussed (`bobby/suggestions.py`; heavily gated — see the module
  docstring for the six gates). Off by default, so the David demo is
  unaffected. Rehearsal checklist: tune `ANALYZE_INTERVAL_SECONDS` and
  `BOBBY_PROACTIVE_COOLDOWN` against real meeting cadence; confirm the
  pitch lands in character; confirm the no-by-default prompt bar is high
  enough that Bobby doesn't offer nonsense.
- **BlackHole → Zoom/Meet capture** (only if DAVE kills Discord receive):
  aggregate device setup in docs/AUDIO_SETUP.md; flip `USE_DEFAULT_MIC`
  in audio_capture.py to env-driven config while at it.
- **ElevenLabs decision**: renew (~$5/mo Starter) for the Borat voice, or
  ship demos on macOS `say`.
- **Local-mode mid-build converse.** Blocked on the local orchestrator's
  synchronous launch_agent; would need the agent subprocess moved to a
  worker thread like Discord mode. Only worth it if local mode ever
  becomes more than a test rig.

## Session-history pointers

- Project memory: `~/.claude/projects/-Users-maximelas-Projects-bobby/memory/`
- Plan file from the revival sprint: `~/.claude/plans/you-are-picking-up-abstract-harp.md`
- The "why" behind every revival change: PR #1's description.
