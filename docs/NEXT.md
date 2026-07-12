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
