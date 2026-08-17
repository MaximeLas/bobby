#!/usr/bin/env python3
"""
Bobby preflight — the go/no-go check to run before every session and demo.

    uv run python3 tools/preflight.py

Exits 0 only when every required check passes. Warnings (⚠️) explain a
misconfiguration without blocking: the live checks below already exercise the
credentials that actually win at runtime.

Why each check exists — every failure below happened for real, 4–17 Aug 2026:

  key drift    load_dotenv() does NOT override an existing shell export, so a
               stale ~/.zshrc copy silently shadows .env. Cost two sessions.
  AAI token    an unfunded account still authenticates everywhere else; only
               the streaming-token endpoint reports "Insufficient funds".
  EL audio     /v1/user/subscription reports a healthy plan even when the key
               itself was minted with credit quota 0, and Bobby's restricted
               key deliberately lacks models_read — so neither endpoint can
               catch the quota trap. Only a real generation can, which is why
               this check spends a fraction of a cent on purpose.
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import dotenv_values, load_dotenv

from bobby.config import PROJECT_ROOT

ENV_FILE = PROJECT_ROOT / ".env"
KEY_NAMES = ("ASSEMBLYAI_API_KEY", "ELEVENLABS_API_KEY")

AAI_TOKEN_URL = "https://streaming.assemblyai.com/v3/token?expires_in_seconds=60"
# Generous enough that a slow network reports a real result, short enough that
# a dead endpoint can't stall a pre-demo check.
NETWORK_TIMEOUT = 10
CLI_TIMEOUT = 15


def _ok(message):
    print(f"✅ {message}")


def _fail(message):
    print(f"❌ {message}")


def _warn(message):
    print(f"⚠️  {message}")


def _info(message):
    print(f"ℹ️  {message}")


def _last4(value):
    """Key fingerprint for logs. Never print more than this."""
    return f"…{value[-4:]}" if value else "(empty)"


def check_key_shadowing(shell_env, file_env):
    """
    Report credentials whose shell copy differs from .env.

    Not a failure: the shell copy is what Bobby will use, so if it works the
    demo works. It is a ⚠️ because when the live checks below DO fail, this
    line is the answer to "but I just fixed that key".

    Returns:
        bool: True when both keys resolve from a single, consistent source
    """
    notes = []

    for name in KEY_NAMES:
        # None = never exported, "" = exported empty (which still shadows .env)
        shell_value = shell_env.get(name)
        file_value = file_env.get(name)

        if shell_value is None:
            continue  # .env is the only source — nothing can shadow it

        if not shell_value:
            where = f".env ({_last4(file_value)})" if file_value else ".env"
            notes.append(
                f"{name}: exported EMPTY in this shell — an empty export still "
                f"shadows {where}, so Bobby starts with no key. Run "
                f"`unset {name}` or give the export a value."
            )
        elif file_value and shell_value != file_value:
            notes.append(
                f"{name}: shell export {_last4(shell_value)} SHADOWS .env "
                f"{_last4(file_value)} — the shell copy wins at runtime "
                f"(load_dotenv does not override). .env is canonical: fix the "
                f"export, or sync .env. Checks below use {_last4(shell_value)}."
            )
        elif not file_value:
            notes.append(
                f"{name}: exported in this shell ({_last4(shell_value)}) but "
                f"absent from .env — any non-interactive launch (launchd, cron, "
                f"a fresh terminal) will start Bobby with no key."
            )

    for note in notes:
        _warn(note)

    if not notes:
        _ok("Credential sources agree (.env is what runs)")

    return not notes


def check_assemblyai(api_key):
    """Request a streaming token — the only endpoint that surfaces funding state."""
    if not api_key:
        _fail("AssemblyAI: no ASSEMBLYAI_API_KEY at runtime — check .env (and any ⚠️ above)")
        return False

    request = urllib.request.Request(AAI_TOKEN_URL, headers={"Authorization": api_key})
    try:
        with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            if response.status == 200:
                _ok(f"AssemblyAI streaming token issued (key {_last4(api_key)})")
                return True
            _fail(f"AssemblyAI: HTTP {response.status} (key {_last4(api_key)})")
            return False

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace").strip()
        _fail(f"AssemblyAI: HTTP {e.code} — {body[:200]} (key {_last4(api_key)})")
        return False
    except Exception as e:
        _fail(f"AssemblyAI: {e} (key {_last4(api_key)})")
        return False


def check_elevenlabs(api_key):
    """Generate two characters of real speech — see the module docstring."""
    if not api_key:
        _fail("ElevenLabs: no ELEVENLABS_API_KEY at runtime — check .env (and any ⚠️ above)")
        return False

    # Imported here, not at module scope: bobby.tts calls load_dotenv() and
    # builds its client at import time, which must happen after the shell
    # snapshot in main().
    from bobby.tts import (
        BOBBY_MODEL,
        BOBBY_VOICE_ID,
        elevenlabs_error_message,
        generate_audio,
    )

    try:
        audio_bytes = generate_audio("ok")
    except Exception as e:
        _fail(f"ElevenLabs: {elevenlabs_error_message(e)} (key {_last4(api_key)})")
        return False

    if not audio_bytes:
        _fail(f"ElevenLabs: generation returned 0 bytes (key {_last4(api_key)})")
        return False

    _ok(
        f"ElevenLabs voice speaks ({len(audio_bytes)} bytes, {BOBBY_MODEL}, "
        f"voice {BOBBY_VOICE_ID}, key {_last4(api_key)})"
    )
    return True


def check_claude_cli():
    """Presence only — Bobby's agents authenticate with Max's own credentials."""
    path = shutil.which("claude")
    if not path:
        _fail("claude CLI not on PATH — Bobby cannot launch or resume agents")
        return False

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT,
        )
    except Exception as e:
        _fail(f"claude CLI at {path} did not run: {e}")
        return False

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        _fail(f"claude --version exited {result.returncode}: {detail[:200]}")
        return False

    _ok(f"claude CLI {result.stdout.strip()} ({path})")
    return True


def check_ffmpeg():
    """Discord-mode dependency only — never fails the local-mode preflight."""
    path = shutil.which("ffmpeg")
    if path:
        _ok(f"ffmpeg present ({path})")
    else:
        _info("ffmpeg not found — Discord voice output would break; local mode is fine")
    return True


def main():
    started = time.monotonic()
    print("Bobby preflight")
    print("=" * 60)

    # Snapshot BEFORE load_dotenv: comparing what the shell already exported
    # against what .env holds is the entire point of check_key_shadowing.
    shell_env = {name: os.environ.get(name) for name in KEY_NAMES}

    if not ENV_FILE.exists():
        _warn(f".env not found at {ENV_FILE} — keys can only come from the shell")
    load_dotenv(ENV_FILE)
    file_env = dotenv_values(ENV_FILE)

    sources_clean = check_key_shadowing(shell_env, file_env)

    # os.environ post-load is the ground truth of what Bobby will use:
    # shell export first, .env second.
    results = [
        check_assemblyai(os.environ.get("ASSEMBLYAI_API_KEY", "")),
        check_elevenlabs(os.environ.get("ELEVENLABS_API_KEY", "")),
        check_claude_cli(),
        check_ffmpeg(),
    ]

    elapsed = time.monotonic() - started
    failed = results.count(False)

    print("=" * 60)
    if failed:
        print(f"NOT READY — {failed} check(s) failed  ({elapsed:.1f}s)")
        return 1

    suffix = "" if sources_clean else " (with ⚠️ above)"
    print(f"GO — all checks passed{suffix}  ({elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
