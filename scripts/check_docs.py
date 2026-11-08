#!/usr/bin/env python3
"""Validate local documentation links and report role-specific reading sizes."""

import json
from pathlib import Path
import re
import sys


def check(root):
    errors = []
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    entry = root / manifest["entry"]
    if manifest["schema_version"] != 1 or not entry.is_file():
        errors.append("배포 manifest 또는 진입 파일이 잘못됐습니다.")
    for folder in ("workflow", "docs", "templates"):
        for path in (root / folder).glob("*.md"):
            content = path.read_text(encoding="utf-8")
            if sum(line.startswith("```") for line in content.splitlines()) % 2:
                errors.append(f"닫히지 않은 코드 블록: {path}")
            for link in re.findall(r"\]\(([^)]+)\)", content):
                if link.startswith(("http://", "https://", "#")):
                    continue
                target = path.parent / link.split("#")[0]
                if not target.is_file():
                    errors.append(f"링크 없음: {path.name} → {link}")
    content = entry.read_text(encoding="utf-8")
    print(f"entry.md: {len(content):,} characters (not tokens)")
    for line in content.splitlines():
        if not line.startswith("| "):
            continue
        links = re.findall(r"\]\(([^)]+\.md)\)", line)
        if not links:
            continue
        files = {entry, *(entry.parent / link for link in links)}
        if all(path.is_file() for path in files):
            total = sum(len(path.read_text(encoding="utf-8")) for path in files)
            print(f"{line.split('|')[1].strip()}: {len(files)} files, {total:,} characters")
    print(f"workflow modules: {len(list((root / 'workflow').glob('*.md')))}")
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(check(Path(__file__).resolve().parents[1]))
