# Launch doc — Bobby demo week (written 17 Aug 2026, evening)

_For the agent picking up demo week in a fresh session. The orientation session that
wrote this ran deep (~440k tokens), so treat this doc as orientation and re-derive
anything load-bearing from the files it points at. `docs/NEXT.md` is the full handoff
playbook; this doc is the "what's next, in order" layer on top of it._

## The mission

Max is **with David (Hamburger) in person this week** and wants Bobby's first
real active-participant demo, targeting the **publico-app** workspace (David's
legal-tech project, Next.js 16, dev server on port 3000). Decisions already made —
do not re-litigate:

- **Vehicle: LOCAL mode, in person** (one MacBook, room mic, speakers). Discord mode
  comes right after, once local goes smoothly — the DAVE voice-receive go/no-go moved
  to that week.
- **Brain stays on the `claude` CLI** (Max's plan, $0 marginal). PR #3's direct-API
  path stays dormant unless `ANTHROPIC_API_KEY` is set. Resolved; no action.
- **ElevenLabs: Starter plan (monthly), restricted key `bobby-local`** — working and
  live-verified 17 Aug (~17:34): the Borat voice test spoke. AssemblyAI: funded, key
  synced into `.env`, streaming token verified 200.

## State as of tonight

- Branch `feature/conversational-bobby` checked out; offline suite **56/56 green**.
- **Three stacked PRs, all still open:** #1 revival (→ main, ready), #2 conversational
  Bobby (draft), #3 backlog burn-down (draft, MERGEABLE/CLEAN — carries the two pieces
  the local demo needs: `bobby/voice.py` local-mode voice parity and `BOBBY_DEV_URL`
  for publico's port 3000).
- Keys live in `.env` (canonical; Max also mirrors them in `~/.zshrc` — same values;
  on rotation update both, see NEXT.md "(17 Aug)" section for the two shadowing traps).
- **Working tree: CLEAN** — the March sandbox residue (HelloWorld page + router +
  react-router-dom) and the stray `tmp/` log were reverted/removed on 17 Aug evening
  with Max's approval. Sandbox is a blank canvas; runtime files there are gitignored.

## The order of work (each step gates the next)

1. **Live checks with Max at the keyboard (~7 min):**
   `uv run python3 tests/manual/test_agent_loop.py` (expects a "Night Shift" page built
   in the sandbox) then `uv run python3 tests/manual/test_brain.py` (one spoken answer).
   These need Max's own terminal (the nested `claude` CLI can't auth from an agent
   sandbox — Keychain). The Discord/DAVE step of the old 25-min checklist is deferred —
   local mode replaced it.
2. **Merge the stack** #1 → #2 → #3 (GitHub retargets automatically). Confirm with Max
   first — one yes covers all three.
3. **Return to main and clean up:** pull, delete the merged branches
   (`revival/universal-3-5-pro`, `feature/conversational-bobby`,
   `claude/bobby-capabilities-av0r9h`), local + remote, with Max's go. From here on,
   work happens on main from first principles.
4. **Build the two small pre-demo items on main** (specs in NEXT.md "(17 Aug)"
   section): `tools/preflight.py` (the EL check MUST be a real tiny TTS generation —
   the subscription endpoint can't see key-level quota; don't probe `/v1/models`, the
   key lacks that scope) and the `tts.py` error-unwrap fix (port
   `discord_bot._speak_in_voice`'s clean `e.body['detail']['message']` handling).
5. **Rehearse solo on sandbox** (full voice loop: trigger → build → spoken completion,
   plus "Hey Bobby, how is it going?" mid-build).
6. **Rehearse on a publico worktree** (commands in NEXT.md demo runbook; add
   `BOBBY_DEV_URL=http://localhost:3000`; main stays untouchable via the worktree).
7. **Go live with David.** Back-pocket features from the 26 Jun call: hero page upgrade
   (safest), drafting-window source footnotes (David explicitly wants it; rehearse first).

Side quests, when convenient:
- **Sweep the 05 Aug session transcript** — the sidebar session named
  "(05 Aug) Sidecar field report → v2 design". Max wants a check (delegate to a
  subagent) for anything said there that never landed in the docs. Expectation: the
  outputs are already captured (`docs/2026-08-05-sidecar-v2-design.md`, the replay
  harness, the 11 Aug v2 implementation), so this is verification, not required
  reading — report only deltas Max needs to know.
- **Rerun the sidecar v2 live check** (command in NEXT.md "(11 Aug)" bullet — the
  account is fixed; the check itself was never rerun). Sidecar remains a live Bobby
  use case (Steven calls) alongside the demo track.

## Pointers

- `docs/NEXT.md` — the playbook: "(17 Aug)" sections for demo-week state/decisions and
  the post-demo backlog (partials-based triggers, Scribe v2 second engine, SDK-upgrade
  audit verdict, voice refresh, ElevenAgents).
- Project memory `MEMORY.md` — one-line-per-fact history including today's key saga.
- ElevenLabs SDK audit (17 Aug, byte-level diff): pinned 2.54.0 is byte-identical to
  2.64.0 on Bobby's whole call surface; Scribe v2 Realtime + Speech-to-Speech already
  in 2.54.0. Upgrade post-demo only.

## Kickoff (paste into the fresh session)

```
Read docs/2026-08-17-demo-week-launch.md and take ownership of Bobby demo week. The tree is clean — start by driving the two live checks with me, then merge the PR stack, bring us back to main with the merged branches cleaned up, build preflight.py and the tts.py error fix, and get us to the sandbox rehearsal. At some point, also run the 05 Aug transcript sweep described in the launch doc's side quests.
```

## Self-epitaph

This session (17 Aug, "Bobby demo-week orientation"): oriented demo week, fixed both
credential systems live (AAI stale-key swap; ElevenLabs resubscribe + quota-0 key trap
+ shell-shadowing diagnosis), decided local-mode/in-person, ran the EL SDK audit, and
captured all state into NEXT.md + this doc. Once this doc is read by the next session,
this one is archivable — nothing load-bearing lives only in its transcript.
