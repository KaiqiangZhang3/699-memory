"""Build a fixture repo from scratch, run its tests, and record the baseline (T06 / C02).

    .venv/bin/python scripts/fixture_baseline.py formal/taskservice

Writes fixtures/baselines/<name>.json (tests, commit, hashes) and <name>.log
(raw pytest output), then updates that fixture's entry in fixtures/manifest.json.
Running it twice on unchanged source gives the same commit SHA and tree hash.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tiered_memory.fixture import FIXTURES_DIR, build_fixture_repo, run_baseline, source_tree_hash  # noqa: E402

MANIFEST = FIXTURES_DIR / "manifest.json"


def main(rel: str) -> int:
    src = FIXTURES_DIR / rel
    if not (src / "pytest.ini").exists():
        print(f"not a fixture: {src}")
        return 2
    name = rel.replace("/", "__")
    manifest = json.loads(MANIFEST.read_text())
    entry = next((f for f in manifest["fixtures"] if f["path"] == f"fixtures/{rel}"), None)
    if entry is None:
        print(f"{rel} is not listed in {MANIFEST}")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        commit = build_fixture_repo(src, repo, f"Initial fixture: {rel}")
        result = run_baseline(repo, Path(tmp) / "junit.xml")

    output = result.pop("_output")
    out_dir = FIXTURES_DIR / "baselines"
    out_dir.mkdir(exist_ok=True)
    result = {"fixture": f"fixtures/{rel}", "source_tree_hash": source_tree_hash(src), **result}
    (out_dir / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    (out_dir / f"{name}.log").write_text(output)

    entry.update({
        "source_tree_hash": result["source_tree_hash"],
        "initial_commit": commit,
        "baseline": {
            "file": f"fixtures/baselines/{name}.json",
            "outcome": result["outcome"],
            "counts": result["counts"],
            "recorded_at_utc": result["ended_at_utc"],
        },
    })
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"{rel}: commit {commit}, {result['counts']}, outcome={result['outcome']}")
    return 0 if result["outcome"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "formal/taskservice"))
