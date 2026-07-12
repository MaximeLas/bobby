#!/usr/bin/env python3
"""
Automated tests for bobby.config

Verifies that config paths resolve correctly and respond to BOBBY_WORKSPACE.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_project_root():
    """PROJECT_ROOT should point to the repo root (contains bobby/ and pyproject.toml)."""
    from bobby.config import PROJECT_ROOT

    assert PROJECT_ROOT.exists(), f"PROJECT_ROOT does not exist: {PROJECT_ROOT}"
    assert (PROJECT_ROOT / "bobby").is_dir(), "PROJECT_ROOT/bobby/ not found"
    assert (PROJECT_ROOT / "pyproject.toml").is_file(), "PROJECT_ROOT/pyproject.toml not found"


def test_default_workspace():
    """Default WORKSPACE_DIR should be PROJECT_ROOT/sandbox."""
    # Only test when BOBBY_WORKSPACE is not set (default behavior)
    if "BOBBY_WORKSPACE" in os.environ:
        return True  # Skip — custom workspace is set

    from bobby import config
    # Reload to get fresh state
    import importlib
    importlib.reload(config)

    assert str(config.WORKSPACE_DIR).endswith("/sandbox"), \
        f"Default workspace should end with /sandbox, got: {config.WORKSPACE_DIR}"


def test_file_paths_derive_from_workspace():
    """All runtime file paths should be children of WORKSPACE_DIR."""
    from bobby.config import WORKSPACE_DIR, TRANSCRIPT_FILE, PROGRESS_FILE, PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE

    for name, path in [
        ("TRANSCRIPT_FILE", TRANSCRIPT_FILE),
        ("PROGRESS_FILE", PROGRESS_FILE),
        ("PAUSE_FLAG_FILE", PAUSE_FLAG_FILE),
        ("BOBBY_SPEECH_FILE", BOBBY_SPEECH_FILE),
    ]:
        assert path.parent == WORKSPACE_DIR, \
            f"{name} parent should be WORKSPACE_DIR, got: {path.parent}"


def test_workspace_override():
    """BOBBY_WORKSPACE env var should override the default workspace."""
    import importlib
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        old_val = os.environ.get("BOBBY_WORKSPACE")
        try:
            os.environ["BOBBY_WORKSPACE"] = tmpdir
            from bobby import config
            importlib.reload(config)

            assert str(config.WORKSPACE_DIR) == str(Path(tmpdir).resolve()), \
                f"WORKSPACE_DIR should be {tmpdir}, got: {config.WORKSPACE_DIR}"
            assert str(config.TRANSCRIPT_FILE).startswith(str(Path(tmpdir).resolve())), \
                f"TRANSCRIPT_FILE should be under {tmpdir}"
        finally:
            # Restore original state
            if old_val is None:
                del os.environ["BOBBY_WORKSPACE"]
            else:
                os.environ["BOBBY_WORKSPACE"] = old_val
            importlib.reload(config)


def test_dev_url_default():
    """Default DEV_SERVER_URL should be the sandbox Vite port."""
    if "BOBBY_DEV_URL" in os.environ:
        return True  # Skip — custom dev URL is set

    from bobby import config
    import importlib
    importlib.reload(config)

    assert config.DEV_SERVER_URL == "http://localhost:5173", \
        f"Default dev URL should be Vite's 5173, got: {config.DEV_SERVER_URL}"


def test_dev_url_override():
    """BOBBY_DEV_URL env var should override the default dev-server URL."""
    import importlib

    old_val = os.environ.get("BOBBY_DEV_URL")
    try:
        os.environ["BOBBY_DEV_URL"] = "http://localhost:3000"
        from bobby import config
        importlib.reload(config)

        assert config.DEV_SERVER_URL == "http://localhost:3000", \
            f"DEV_SERVER_URL should be overridden, got: {config.DEV_SERVER_URL}"
    finally:
        if old_val is None:
            del os.environ["BOBBY_DEV_URL"]
        else:
            os.environ["BOBBY_DEV_URL"] = old_val
        importlib.reload(config)


ALL_TESTS = [
    ("PROJECT_ROOT resolves correctly", test_project_root),
    ("Default workspace is sandbox/", test_default_workspace),
    ("File paths derive from WORKSPACE_DIR", test_file_paths_derive_from_workspace),
    ("BOBBY_WORKSPACE env var overrides default", test_workspace_override),
    ("Default dev URL is Vite's 5173", test_dev_url_default),
    ("BOBBY_DEV_URL env var overrides default", test_dev_url_override),
]
