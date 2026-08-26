#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".hypothesis",
    ".venv",
    "build",
    "dist",
}


def collected_test_count() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    if not match:
        raise RuntimeError("could not determine pytest collection count")
    return int(match.group(1))


def update_demo_count(total: int) -> None:
    path = ROOT / "scripts" / "demo60.py"
    text = path.read_text()
    pattern = re.compile(r'"\s*\d+ tests, (\d+) red team attacks, (\d+)/(\d+) mutations caught"')
    match = pattern.search(text)
    if not match:
        raise RuntimeError("could not find demo60 closing count line")
    attacks, caught, mutations = match.groups()
    replacement = f'"{total} tests, {attacks} red team attacks, {caught}/{mutations} mutations caught"'
    path.write_text(pattern.sub(replacement, text, count=1))


def is_shipped(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if not path.is_file():
        return False
    if relative.as_posix() == "SHA256SUMS.txt":
        return False
    if any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in relative.parts):
        return False
    if relative.as_posix().startswith(("outputs/generated", "outputs/demo")):
        return False
    if relative.suffix == ".pyc":
        return False
    return True


def refresh_manifest() -> int:
    entries: list[tuple[str, str]] = []
    for path in sorted(ROOT.rglob("*")):
        if not is_shipped(path):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append((path.relative_to(ROOT).as_posix(), digest))
    manifest = "".join(f"{digest}  {relative}\n" for relative, digest in entries)
    (ROOT / "SHA256SUMS.txt").write_text(manifest)
    return len(entries)


def main() -> int:
    total = collected_test_count()
    update_demo_count(total)
    entries = refresh_manifest()
    print(f"updated demo60 test count to {total}")
    print(f"wrote SHA256SUMS.txt with {entries} shipped-file entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
