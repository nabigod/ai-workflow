#!/usr/bin/env python3
"""Read-only workflow MCP server using only the Python standard library."""

import argparse
import datetime
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path, PurePosixPath
import re
import sys


PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_REQUEST = 64 * 1024
COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def confined(root, relative):
    """Reject symlinks and traversal, including Windows path spellings."""
    path = PurePosixPath(relative)
    if (not relative or path.is_absolute() or ".." in path.parts
            or "\\" in relative or ":" in relative):
        raise ValueError("배포 묶음 안의 상대 경로만 사용할 수 있습니다.")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("심볼릭 링크는 읽지 않습니다.")
    if not target.resolve().is_relative_to(root):
        raise ValueError("배포 묶음 밖의 파일은 읽지 않습니다.")
    return target


class WorkflowReader:
    def __init__(self, state):
        self.state = Path(state).resolve()

    def snapshot(self, commit):
        if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
            raise ValueError("축약하지 않은 Git 커밋을 지정하세요.")
        snapshot = confined(self.state, "snapshots/" + commit)
        if not snapshot.is_dir():
            raise ValueError("요청한 고정 스냅샷이 없습니다. 최신 버전으로 대체하지 않습니다.")
        manifest = json.loads(confined(snapshot, "manifest.json").read_text(encoding="utf-8"))
        if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
                or manifest.get("entry") != "workflow/entry.md"):
            raise ValueError("지원하지 않는 배포 manifest입니다.")
        return snapshot

    def status(self):
        active_path = confined(self.state, "active.json")
        status_path = confined(self.state, "sync-status.json")
        active = json.loads(active_path.read_text(encoding="utf-8"))
        snapshot = self.snapshot(active["commit"])
        if (active.get("schema_version") != 1 or Path(active["snapshot"]) != snapshot
                or Path(active["entry"]) != snapshot / "workflow/entry.md"):
            raise ValueError("active.json의 경로와 선택한 스냅샷이 일치하지 않습니다.")
        return {
            "active": active,
            "sync_status": json.loads(status_path.read_text(encoding="utf-8")),
            "active_path_on_host": str(active_path),
            "sync_status_path_on_host": str(status_path),
            "entry": "workflow/entry.md",
            "snapshot_uri": f"workflow://{active['commit']}/",
            "observed_at": timestamp(),
            "remote_checked_this_call": False,
            "read_files": [str(active_path), str(status_path), str(snapshot / "manifest.json")],
        }

    def document(self, commit, path):
        if not isinstance(path, str):
            raise ValueError("문서 경로는 문자열이어야 합니다.")
        relative = PurePosixPath(path)
        if (len(relative.parts) != 2 or relative.parts[0] not in ("workflow", "docs")
                or relative.suffix != ".md"):
            raise ValueError("workflow/ 또는 docs/ 안의 Markdown 문서만 읽을 수 있습니다.")
        snapshot = self.snapshot(commit)
        target = confined(snapshot, path)
        body = target.read_bytes()
        return {
            "commit": commit, "path": path,
            "uri": f"workflow://{commit}/{path}",
            "path_on_host": str(target),
            "read_at": timestamp(), "sha256": hashlib.sha256(body).hexdigest(),
            "text": body.decode("utf-8"),
        }


TOOLS = [
    {
        "name": "get_workflow_status",
        "description": "PC의 active.json과 sync-status.json 본문을 읽습니다. 원격 동기화나 entry 본문 읽기는 하지 않습니다.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "read_workflow_document",
        "description": "지정한 고정 Git 커밋에서 역할 문서 본문을 읽습니다. 먼저 workflow/entry.md를 읽고 필요한 문서만 요청하세요.",
        "inputSchema": {
            "type": "object", "properties": {
                "commit": {"type": "string", "description": "고정한 전체 Git 커밋"},
                "path": {"type": "string", "description": "예: workflow/entry.md, workflow/execution.md"},
            }, "required": ["commit", "path"], "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]


def error_reply(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def dispatch(reader, message):
    if (not isinstance(message, dict) or message.get("jsonrpc") != "2.0"
            or not isinstance(message.get("method"), str)
            or ("id" in message and (isinstance(message["id"], bool)
                                    or not isinstance(message["id"], (str, int))))):
        return error_reply(None, -32600, "Invalid Request")
    # Notifications never produce JSON-RPC responses, including unknown notifications.
    if "id" not in message:
        return None
    request_id, method = message["id"], message["method"]
    params = message.get("params", {})
    if not isinstance(params, dict):
        return error_reply(request_id, -32602, "params must be an object")
    if method == "initialize":
        requested = params.get("protocolVersion")
        result = {
            "protocolVersion": requested if requested in PROTOCOLS else PROTOCOLS[0],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ai-workflow", "version": "1.0.0"},
            "instructions": "Read workflow/entry.md at an explicit commit, then only the documents required for your role. Host paths are not paths on the SSH server.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name, arguments = params.get("name"), params.get("arguments", {})
        if not isinstance(arguments, dict):
            return error_reply(request_id, -32602, "arguments must be an object")
        if not isinstance(name, str) or name not in {tool["name"] for tool in TOOLS}:
            return error_reply(request_id, -32602, "Unknown tool")
        try:
            if name == "get_workflow_status":
                if arguments:
                    raise ValueError("이 도구는 인자를 받지 않습니다.")
                value = reader.status()
            else:
                if set(arguments) != {"commit", "path"}:
                    raise ValueError("commit과 path를 명시하세요.")
                value = reader.document(arguments["commit"], arguments["path"])
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
                      "isError": False}
        except (OSError, ValueError, KeyError, TypeError) as error:
            result = {"content": [{"type": "text", "text": str(error)}], "isError": True}
    else:
        return error_reply(request_id, -32601, "Method not found")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def stdio(reader, source=None, sink=None):
    source = source or sys.stdin.buffer
    sink = sink or sys.stdout.buffer
    while True:
        line = source.readline(MAX_REQUEST + 1)
        if not line:
            return
        if len(line) > MAX_REQUEST:
            # Do not process the remainder as another request.
            raise ValueError("MCP 요청 크기 제한을 초과했습니다.")
        try:
            message = json.loads(line)
        except (ValueError, UnicodeError):
            reply = error_reply(None, -32700, "Parse error")
        else:
            reply = dispatch(reader, message)
        if reply is not None:
            sink.write((json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8"))
            sink.flush()


def http_server(reader, token, port=8765):
    """Stateless Streamable HTTP, JSON responses; reach remotely via SSH forwarding."""
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("32자 이상의 ASCII 인증 토큰이 필요합니다.")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            # No headers, token, document bodies, or client-supplied paths in logs.
            pass

        def reply(self, status, value=None):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8") if value is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if status == 405:
                self.send_header("Allow", "POST")
            self.end_headers()
            self.wfile.write(body)

        def permitted(self):
            if self.path != "/mcp":
                self.reply(404)
                return False
            # Native MCP clients do not send Origin. Reject browser origins entirely.
            if self.headers.get("Origin") is not None:
                self.reply(403)
                return False
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + token).encode("ascii")):
                self.reply(401)
                return False
            if self.headers.get("MCP-Protocol-Version", "2025-03-26") not in PROTOCOLS:
                self.reply(400)
                return False
            return True

        def do_POST(self):
            if not self.permitted():
                return
            if self.headers.get_content_type() != "application/json":
                self.reply(415)
                return
            accept = self.headers.get("Accept", "")
            if "application/json" not in accept or "text/event-stream" not in accept:
                self.reply(406)
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self.reply(400)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.reply(400)
                return
            if not 0 < length <= MAX_REQUEST:
                self.reply(413)
                return
            self.connection.settimeout(10)
            try:
                message = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeError, OSError):
                self.reply(400, error_reply(None, -32700, "Parse error"))
                return
            reply = dispatch(reader, message)
            self.reply(202 if reply is None else 200, reply)

        def do_GET(self):
            if self.permitted():
                self.reply(405)

        def do_DELETE(self):
            if self.permitted():
                self.reply(405)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token-file", type=Path)
    args = parser.parse_args()
    try:
        reader = WorkflowReader(args.state_dir)
        if args.transport == "stdio":
            stdio(reader)
        else:
            token_file = args.token_file or args.state_dir / "mcp-token"
            if token_file.is_symlink():
                raise ValueError("토큰 파일 심볼릭 링크는 사용할 수 없습니다.")
            token = token_file.read_text(encoding="utf-8").strip()
            with http_server(reader, token, args.port) as server:
                print(f"Workflow MCP: http://127.0.0.1:{server.server_port}/mcp (read-only)", file=sys.stderr)
                server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
