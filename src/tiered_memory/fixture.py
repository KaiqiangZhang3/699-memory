"""Build isolated fixture repositories and record their baseline test runs (task T06).

Every run starts from a fresh copy of the same fixture (proposal 4.8). The
initial commit uses a fixed author, committer and date, so the same fixture
source always produces the same commit SHA. Evidence can then cite that SHA
(decision D5).
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .usage import utc_now_iso

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures"
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.db", ".DS_Store")

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Fixture Builder",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": "2026-11-01T00:00:00+00:00",
    "GIT_COMMITTER_NAME": "Fixture Builder",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_DATE": "2026-11-01T00:00:00+00:00",
}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fixture_files(src: Path) -> list[Path]:
    files = []
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if path.is_file() and not any(part in {"__pycache__", ".pytest_cache"} for part in rel.parts) \
                and path.suffix not in {".pyc", ".db"} and path.name != ".DS_Store":
            files.append(rel)
    return files


def source_tree_hash(src: Path) -> str:
    """sha256 over 'relative/path<TAB>sha256(content)' lines, sorted by path."""
    lines = [f"{rel.as_posix()}\t{hashlib.sha256((src / rel).read_bytes()).hexdigest()}" for rel in fixture_files(src)]
    return sha256_bytes("\n".join(lines).encode())


def _git(dest: Path, *args: str) -> str:
    env = {**os.environ, **GIT_IDENTITY, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    result = subprocess.run(["git", *args], cwd=dest, env=env, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def build_fixture_repo(src: Path, dest: Path, message: str) -> str:
    """Copy src to an empty dest, create one deterministic commit, and return its SHA."""
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"{dest} is not empty")
    shutil.copytree(src, dest, ignore=IGNORED, dirs_exist_ok=True)
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "--no-gpg-sign", "-m", message)
    return _git(dest, "rev-parse", "HEAD")


def _nodeid(classname: str, name: str) -> str:
    parts = classname.split(".")
    # "tests.test_auth" -> "tests/test_auth.py"; "tests.test_x.TestCls" -> "tests/test_x.py::TestCls"
    for i in range(len(parts), 0, -1):
        if parts[i - 1].startswith("test"):
            module = "/".join(parts[:i]) + ".py"
            rest = parts[i:]
            return "::".join([module, *rest, name])
    return f"{classname}::{name}"


def run_baseline(repo: Path, junit_path: Path) -> dict[str, Any]:
    """Run pytest in a fixture repo and return a record whose fields fit evidence_ref (D5)."""
    started = utc_now_iso()
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit_path}"],
        cwd=repo, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    duration_ms = round((time.monotonic() - t0) * 1000, 3)
    output = proc.stdout + proc.stderr

    tests = []
    for case in ET.parse(junit_path).getroot().iter("testcase"):
        if case.find("failure") is not None:
            outcome = "fail"
        elif case.find("error") is not None:
            outcome = "error"
        elif case.find("skipped") is not None:
            outcome = "skipped"
        else:
            outcome = "pass"
        tests.append({"nodeid": _nodeid(case.get("classname", ""), case.get("name", "")), "outcome": outcome})

    return {
        "commit": _git(repo, "rev-parse", "HEAD"),
        "command": "python -m pytest -q",
        "started_at_utc": started,
        "ended_at_utc": utc_now_iso(),
        "duration_ms": duration_ms,
        "exit_code": proc.returncode,
        "outcome": "pass" if proc.returncode == 0 else "fail",
        "tests": sorted(tests, key=lambda t: t["nodeid"]),
        "counts": {k: sum(t["outcome"] == k for t in tests) for k in ("pass", "fail", "error", "skipped")},
        "output_sha256": sha256_bytes(output.encode()),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "_output": output,
    }
