#!/usr/bin/env python3
"""Fetch versioned workflow snapshots and prepare local agent instructions."""

import argparse
import contextlib
import datetime
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile


BEGIN = "<!-- phase-agent-workflow:begin -->"
END = "<!-- phase-agent-workflow:end -->"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=120,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RuntimeError(f"심볼릭 링크에는 쓰지 않습니다: {path}")
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    write_atomic(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


@contextlib.contextmanager
def exclusive(state):
    state.mkdir(parents=True, exist_ok=True)
    lock = state / ".sync-lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise RuntimeError(f"다른 갱신이 진행 중이거나 남은 잠금이 있습니다: {lock}") from None
    try:
        write_json(lock / "owner.json", {"pid": os.getpid(), "started_at": now()})
        yield
    finally:
        shutil.rmtree(lock)


def archive_files(repo, commit):
    archive = zipfile.ZipFile(io.BytesIO(git(repo, "archive", "--format=zip", commit)))
    files = {}
    names = set()
    with archive:
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                    or ":" in item.filename or stat.S_ISLNK(item.external_attr >> 16)):
                raise RuntimeError(f"배포할 수 없는 경로: {item.filename}")
            if item.is_dir():
                continue
            key = item.filename.casefold()
            if key in names:
                raise RuntimeError(f"중복 배포 경로: {item.filename}")
            names.add(key)
            files[item.filename] = archive.read(item)
    manifest = json.loads(files["manifest.json"])
    if manifest.get("schema_version") != 1 or manifest.get("entry") != "workflow/entry.md":
        raise RuntimeError("지원하지 않는 배포 manifest입니다.")
    for required in (manifest["entry"], "templates/entry-instructions.md", "scripts/workflow.py"):
        if required not in files:
            raise RuntimeError(f"배포 파일 누락: {required}")
    return files, manifest


def verify_snapshot(snapshot, expected):
    actual = {}
    for path in snapshot.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"스냅샷 안에 심볼릭 링크가 있습니다: {path}")
        if path.is_file():
            actual[path.relative_to(snapshot).as_posix()] = path.read_bytes()
    if actual != expected:
        raise RuntimeError(f"고정 스냅샷이 변경되었습니다. 덮어쓰지 않습니다: {snapshot}")


def sync(repo, state, branch="main", offline=False):
    repo, state = Path(repo).resolve(), Path(state).resolve()
    with exclusive(state):
        try:
            git(repo, "check-ref-format", "--branch", branch)
            if not offline:
                git(repo, "fetch", "--no-tags", "origin",
                    f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
            revision = "HEAD" if offline else f"refs/remotes/origin/{branch}"
            commit = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
            files, manifest = archive_files(repo, commit)
            snapshots = state / "snapshots"
            snapshots.mkdir(exist_ok=True)
            snapshot = snapshots / commit
            if snapshot.is_symlink():
                raise RuntimeError("스냅샷 심볼릭 링크는 사용할 수 없습니다.")
            if snapshot.exists():
                verify_snapshot(snapshot, files)
            else:
                temporary = Path(tempfile.mkdtemp(prefix=".prepare-", dir=snapshots))
                try:
                    for name, content in files.items():
                        target = temporary / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(content)
                    verify_snapshot(temporary, files)
                    os.replace(temporary, snapshot)
                finally:
                    if temporary.exists():
                        shutil.rmtree(temporary)
            active = {
                "schema_version": 1, "revision": manifest["revision"],
                "layout_version": manifest["layout_version"], "commit": commit,
                "snapshot": str(snapshot), "entry": str(snapshot / manifest["entry"]),
                "repository": str(repo), "branch": branch, "activated_at": now(),
                "remote_checked_at": None if offline else now(),
                "source": "local-head" if offline else "remote-branch",
            }
            write_json(state / "active.json", active)
            write_json(state / "sync-status.json", {
                "checked_at": now(), "ok": True, "remote_checked": not offline,
                "commit": commit,
            })
            return active
        except Exception as error:
            write_json(state / "sync-status.json", {
                "checked_at": now(), "ok": False, "remote_checked": False,
                "error": str(error),
            })
            raise


def command_text(args, shell):
    if shell == "bash":
        return shlex.join(args)
    return "& " + " ".join("'" + value.replace("'", "''") + "'" for value in args)


def render(state, shell):
    state = Path(state).resolve()
    active = json.loads((state / "active.json").read_text(encoding="utf-8"))
    snapshot = Path(active["snapshot"])
    template = (snapshot / "templates/entry-instructions.md").read_text(encoding="utf-8")
    command = command_text([
        sys.executable, str(snapshot / "scripts/workflow.py"), "sync",
        "--repo", active["repository"], "--state-dir", str(state),
        "--branch", active["branch"],
    ], shell)
    text = template.replace("{{ACTIVE_PATH}}", str(state / "active.json"))
    text = text.replace("{{SYNC_COMMAND}}", command)
    for tool in ("codex", "cursor"):
        write_atomic(state / "connectors" / (tool + ".md"), text.encode())
    return text


def merge_instructions(existing, instructions):
    if existing.count(BEGIN) != existing.count(END) or existing.count(BEGIN) > 1:
        raise RuntimeError("기존 연결 지침의 경계가 불명확합니다. 수동 확인이 필요합니다.")
    if BEGIN in existing:
        start, end_start = existing.index(BEGIN), existing.index(END)
        if end_start < start:
            raise RuntimeError("기존 연결 지침의 경계 순서가 잘못됐습니다.")
        end = end_start + len(END)
        outside = existing[:start] + existing[end:]
    else:
        outside = existing
    if "name: phase-agent-workflow" in outside or "# 단계별 에이전트 운영" in outside:
        raise RuntimeError("기존 전체 워크플로우가 있습니다. 백업 후 해당 본문을 짧은 연결 지침으로 교체해야 합니다.")
    if BEGIN in existing:
        return existing[:start] + instructions.strip() + existing[end:]
    return existing + ("\n\n" if existing and not existing.endswith("\n\n") else "") + instructions


def install_codex(state, shell, codex_home=None):
    home = Path(codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser().resolve()
    with exclusive(Path(state).resolve()):
        if (home / "AGENTS.override.md").exists():
            raise RuntimeError("AGENTS.override.md가 있어 AGENTS.md가 가려질 수 있습니다. 먼저 수동 확인하세요.")
        instructions = render(state, shell)
        path = home / "AGENTS.md"
        if path.is_symlink():
            raise RuntimeError("기존 AGENTS.md가 심볼릭 링크입니다. 자동 변경하지 않습니다.")
        original = path.read_bytes() if path.exists() else b""
        merged = merge_instructions(original.decode("utf-8"), instructions).encode()
        if merged == original:
            return path
        if path.exists():
            backup = path.with_name(path.name + ".bak-" + uuid.uuid4().hex)
            backup.write_bytes(original)
        write_atomic(path, merged)
        return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    update = commands.add_parser("sync", help="원격 확인과 커밋별 스냅샷 생성")
    update.add_argument("--repo", required=True, type=Path)
    update.add_argument("--state-dir", required=True, type=Path)
    update.add_argument("--branch", default="main")
    update.add_argument("--offline", action="store_true", help="원격 확인 없이 로컬 HEAD 사용")
    for name in ("render", "install-codex"):
        action = commands.add_parser(name)
        action.add_argument("--state-dir", required=True, type=Path)
        action.add_argument("--shell", choices=("bash", "powershell"), required=True)
        if name == "install-codex":
            action.add_argument("--codex-home", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "sync":
            print(json.dumps(sync(args.repo, args.state_dir, args.branch, args.offline), ensure_ascii=False, indent=2))
        elif args.action == "render":
            print(render(args.state_dir, args.shell))
        else:
            print(install_codex(args.state_dir, args.shell, args.codex_home))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired, zipfile.BadZipFile) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
