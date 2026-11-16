#!/usr/bin/env python3
"""Check documentation and measure explicitly selected reading paths, not tokens."""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote


LINK = re.compile(r"\]\(([^)]+)\)")


def tables(text):
    sections = {}
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("| "):
            sections.setdefault(section, []).append(
                [cell.strip() for cell in line.strip("|").split("|")])
    return sections


def documents(cell):
    return [link.split("#")[0] for link in LINK.findall(cell)
            if not link.startswith(("https://", "http://", "#"))]


def reading_policy(root):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("entry") != "workflow/entry.md":
        raise ValueError("배포 manifest 또는 진입 파일이 잘못됐습니다.")
    entry = root / manifest["entry"]
    sections = tables(entry.read_text(encoding="utf-8"))
    roles = {}
    # Older snapshots have only a role table, without named sections.
    rows = sections.get("역할별 필수 문서", sum(sections.values(), []))
    for row in rows:
        if len(row) == 2 and documents(row[1]):
            roles[row[0]] = documents(row[1])
    environments = {row[0]: documents(row[1])
                    for row in sections.get("환경 프로필", [])
                    if len(row) == 2 and documents(row[1])}
    conditions = {}
    for row in sections.get("조건부 문서", []):
        if len(row) == 4 and documents(row[3]):
            conditions[row[0].strip("`")] = {
                "roles": row[1].split(", "), "when": row[2],
                "documents": documents(row[3]),
            }
    if not roles:
        raise ValueError("역할별 필수 문서가 없습니다.")
    if "역할별 필수 문서" in sections:
        if set(environments) != {"codex", "cursor"}:
            raise ValueError("codex/cursor 환경 프로필이 모두 필요합니다.")
        for condition, rule in conditions.items():
            if set(rule["roles"]) - set(roles) - {"전체"}:
                raise ValueError(f"조건의 역할이 잘못됐습니다: {condition}")
    return entry, roles, environments, conditions


def reading_report(root, environment, role, conditions=(), retained=()):
    entry, roles, environments, rules = reading_policy(root)
    if role not in roles:
        raise ValueError(f"알 수 없는 역할: {role}")
    if environment not in ("codex", "cursor"):
        raise ValueError(f"알 수 없는 환경: {environment}")
    selected = [entry, *(entry.parent / name for name in roles[role])]
    if "models.md" in roles[role] and environments:
        if environment not in environments:
            raise ValueError(f"환경 프로필 누락: {environment}")
        selected.extend(entry.parent / name for name in environments[environment])
    for condition in dict.fromkeys(conditions):
        if condition not in rules:
            raise ValueError(f"알 수 없는 읽기 조건: {condition}")
        rule = rules[condition]
        if role not in rule["roles"] and "전체" not in rule["roles"]:
            raise ValueError(f"{role}에 적용할 수 없는 조건: {condition}")
        if condition == "codex-limit" and environment != "codex":
            raise ValueError("codex-limit은 Codex에만 적용합니다.")
        selected.extend(entry.parent / name for name in rule["documents"])
    unique = sorted(set(selected))
    relative = {path: path.relative_to(root).as_posix() for path in unique}
    retained = set(retained)
    unknown = retained - set(relative.values())
    if unknown:
        raise ValueError(f"선택한 읽기 묶음에 없는 retained 경로: {sorted(unknown)}")
    lengths = {relative[path]: len(path.read_text(encoding="utf-8")) for path in unique}
    return {
        "environment": environment, "role": role, "conditions": list(dict.fromkeys(conditions)),
        "files": lengths, "characters": sum(lengths.values()),
        "duplicate_references": len(selected) - len(unique),
        "retained_files": sorted(retained),
        "read_characters": sum(size for name, size in lengths.items() if name not in retained),
        "tokens": None,
        "excluded": ["전역 지침", "프로젝트 입력·증빙", "도구 응답 포장", "인계·모델 출력·추론"],
    }


def anchors(text):
    result = set(re.findall(r'<a\s+id="([^"]+)"', text))
    counts = {}
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if fenced or not re.match(r"^#{1,6} ", line):
            continue
        heading = re.sub(r"^#+ ", "", line).strip().lower()
        heading = re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")
        count = counts.get(heading, 0)
        counts[heading] = count + 1
        result.add(heading if not count else f"{heading}-{count}")
    return result


def validate(root):
    errors = []
    paths = [root / name for name in ("README.md", "AGENTS.md")]
    for folder in ("workflow", "docs", "templates", "examples"):
        paths.extend((root / folder).rglob("*.md"))
    for path in paths:
        if not path.is_file():
            errors.append(f"문서 없음: {path.relative_to(root)}")
            continue
        content = path.read_text(encoding="utf-8")
        if sum(line.startswith("```") for line in content.splitlines()) % 2:
            errors.append(f"닫히지 않은 코드 블록: {path.relative_to(root)}")
        for link in LINK.findall(content):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*://", link):
                continue
            name, _, anchor = unquote(link).partition("#")
            target = path.parent / name if name else path
            if not target.is_file():
                errors.append(f"링크 없음: {path.relative_to(root)} → {link}")
            elif anchor and target.suffix == ".md":
                if anchor not in anchors(target.read_text(encoding="utf-8")):
                    errors.append(f"앵커 없음: {path.relative_to(root)} → {link}")
    return errors


def check(root, environment="both", role=None, conditions=(), retained=(), as_json=False):
    errors = validate(root)
    reports = []
    try:
        _, roles, _, _ = reading_policy(root)
        for env in ("codex", "cursor") if environment == "both" else (environment,):
            for selected_role in (role,) if role else roles:
                reports.append(reading_report(root, env, selected_role, conditions, retained))
    except (OSError, ValueError, KeyError) as exc:
        errors.append(str(exc))
    if as_json:
        print(json.dumps({"reports": reports, "errors": errors}, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(f"{report['environment']} / {report['role']}: "
                  f"{len(report['files'])} files, {report['characters']:,} characters; "
                  f"read {report['read_characters']:,} (not tokens)")
        for error in errors:
            print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("codex", "cursor", "both"), default="both")
    parser.add_argument("--role", help="entry.md의 역할 이름")
    parser.add_argument("--condition", action="append", default=[], help="entry.md의 조건 ID")
    parser.add_argument("--retained", action="append", default=[],
                        help="동일 버전 본문이 현재 컨텍스트에 남은 저장소 상대 경로")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    sys.exit(check(Path(__file__).resolve().parents[1], args.environment, args.role,
                   args.condition, args.retained, args.json))
