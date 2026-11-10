import copy
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest


SOURCE = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SOURCE / "scripts" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


workflow = module("workflow", "workflow.py")
mcp = module("workflow_mcp", "workflow_mcp.py")


class MCPFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "runtime with spaces"
        self.commit = "a" * 40
        self.snapshot = self.state / "snapshots" / self.commit
        (self.snapshot / "workflow").mkdir(parents=True)
        (self.snapshot / "manifest.json").write_text(json.dumps({
            "schema_version": 1, "entry": "workflow/entry.md",
        }), encoding="utf-8")
        (self.snapshot / "workflow/entry.md").write_bytes((SOURCE / "workflow/entry.md").read_bytes())
        (self.snapshot / "workflow/execution.md").write_text("실행 규칙 원문\n", encoding="utf-8")
        self.active = {
            "schema_version": 1, "commit": self.commit,
            "snapshot": str(self.snapshot), "entry": str(self.snapshot / "workflow/entry.md"),
            "remote_checked_at": "2026-11-08T00:00:00+00:00",
        }
        workflow.write_json(self.state / "active.json", self.active)
        workflow.write_json(self.state / "sync-status.json", {
            "ok": False, "remote_checked": False, "checked_at": "2026-11-09T00:00:00+00:00",
            "error": "fetch failed",
        })
        self.reader = mcp.WorkflowReader(self.state)

    def call(self, name, arguments=None):
        return mcp.dispatch(self.reader, {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })


class MCPTests(MCPFixture):
    def test_status_reads_json_without_claiming_entry_read_or_remote_check(self):
        result = self.reader.status()
        self.assertEqual(result["active"]["commit"], self.commit)
        self.assertFalse(result["sync_status"]["ok"])
        self.assertFalse(result["remote_checked_this_call"])
        self.assertEqual(result["active"]["remote_checked_at"], self.active["remote_checked_at"])
        self.assertNotIn(self.active["entry"], result["read_files"])
        self.assertEqual(set(result["read_files"]), {
            str(self.state / "active.json"), str(self.state / "sync-status.json"),
            str(self.snapshot / "manifest.json"),
        })
        self.assertIn("observed_at", result)

    def test_document_returns_original_body_and_read_evidence(self):
        result = self.reader.document(self.commit, "workflow/execution.md")
        self.assertEqual(result["text"], "실행 규칙 원문\n")
        self.assertEqual(result["commit"], self.commit)
        self.assertIn("read_at", result)
        self.assertEqual(len(result["sha256"]), 64)
        self.assertEqual(result["uri"], f"workflow://{self.commit}/workflow/execution.md")

    def test_pinned_read_survives_active_switch_and_missing_active(self):
        changed = copy.deepcopy(self.active)
        changed["commit"] = "b" * 40
        workflow.write_json(self.state / "active.json", changed)
        result = self.reader.document(self.commit, "workflow/execution.md")
        self.assertEqual(result["commit"], self.commit)
        (self.state / "active.json").unlink()
        self.assertEqual(self.reader.document(self.commit, "workflow/execution.md")["text"], result["text"])
        with self.assertRaisesRegex(ValueError, "최신 버전으로 대체하지"):
            self.reader.document("b" * 40, "workflow/entry.md")

    def test_rejects_traversal_host_paths_scripts_and_arbitrary_commits(self):
        for path in ("../active.json", "/etc/passwd", "workflow/../../secret.md",
                     "workflow/../secret.md", "workflow/..\\secret.md", "docs/C:secret.md",
                     "C:\\Users\\Fadu\\secret.md", "scripts/workflow.py", "active.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.reader.document(self.commit, path)
        for commit in ("main", "HEAD", "aaaa", "../outside", 3, None):
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                self.reader.document(commit, "workflow/entry.md")

    def test_symlink_document_and_snapshot_are_rejected(self):
        outside = self.root / "secret.md"
        outside.write_text("private", encoding="utf-8")
        link = self.snapshot / "workflow/secret.md"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(ValueError, "심볼릭 링크"):
            self.reader.document(self.commit, "workflow/secret.md")
        other = self.state / "snapshots" / ("c" * 40)
        other.symlink_to(self.snapshot, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "심볼릭 링크"):
            self.reader.document("c" * 40, "workflow/entry.md")

    def test_status_rejects_manifest_path_to_another_host_location(self):
        self.active["entry"] = str(self.root / "secret.md")
        workflow.write_json(self.state / "active.json", self.active)
        with self.assertRaisesRegex(ValueError, "일치하지"):
            self.reader.status()

    def test_rpc_errors_and_read_only_tool_surface(self):
        tools = mcp.dispatch(self.reader, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual({tool["name"] for tool in tools["result"]["tools"]},
                         {"get_workflow_status", "read_workflow_document"})
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools["result"]["tools"]))
        self.assertTrue(self.call("read_workflow_document")["result"]["isError"])
        self.assertEqual(self.call("sync")["error"]["code"], -32602)
        self.assertEqual(self.call([])["error"]["code"], -32602)
        self.assertEqual(mcp.dispatch(self.reader, [1, 2])["error"]["code"], -32600)
        reply = mcp.dispatch(self.reader, {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": []})
        self.assertEqual(reply["error"]["code"], -32602)
        for arguments in ({"commit": self.commit, "path": []}, {"commit": [], "path": "workflow/entry.md"}):
            self.assertTrue(self.call("read_workflow_document", arguments)["result"]["isError"])

    def test_stdio_process_initialize_notifications_and_document_call(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "read_workflow_document", "arguments": {"commit": self.commit, "path": "workflow/execution.md"}}},
        ]
        process = subprocess.run([
            sys.executable, str(SOURCE / "scripts/workflow_mcp.py"), "--state-dir", str(self.state),
        ], input="".join(json.dumps(message) + "\n" for message in messages).encode(),
            capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-03-26")
        value = json.loads(replies[1]["result"]["content"][0]["text"])
        self.assertEqual(value["text"], "실행 규칙 원문\n")

    def test_stdio_parse_errors_are_json_and_stream_continues(self):
        source = io.BytesIO(b'broken\n{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
        sink = io.BytesIO()
        mcp.stdio(self.reader, source, sink)
        replies = [json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["result"], {})

    def test_prepare_is_private_and_does_not_change_active_or_codex_connector(self):
        before = (self.state / "active.json").read_bytes()
        (self.state / "connectors").mkdir()
        codex = self.state / "connectors/codex.md"
        codex.write_text("existing codex", encoding="utf-8")
        paths = workflow.prepare_mcp(self.state)
        self.assertEqual(len(paths), 3)
        token = (self.state / "mcp-token").read_bytes()
        workflow.prepare_mcp(self.state)
        self.assertEqual((self.state / "mcp-token").read_bytes(), token)
        self.assertEqual((self.state / "active.json").read_bytes(), before)
        self.assertEqual(codex.read_text(encoding="utf-8"), "existing codex")
        stdio = json.loads(paths[0].read_text(encoding="utf-8"))["mcpServers"]["ai-workflow"]
        self.assertEqual(stdio["command"], sys.executable)
        self.assertEqual(stdio["args"][-1], str(self.state))
        self.assertNotIn("{{", paths[2].read_text(encoding="utf-8"))
        if os.name != "nt":
            for path in [self.state / "mcp-token", paths[0], paths[1]]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_install_preserves_other_mcp_servers_backs_up_and_is_idempotent(self):
        config = self.root / "cursor settings/mcp.json"
        config.parent.mkdir()
        original = b'\xef\xbb\xbf{"mcpServers":{"other":{"command":"keep"}},"custom":true}\r\n'
        config.write_bytes(original)
        workflow.install_cursor_mcp(self.state, config=config)
        installed = config.read_bytes()
        value = json.loads(installed)
        self.assertEqual(value["mcpServers"]["other"], {"command": "keep"})
        self.assertTrue(value["custom"])
        backups = list(config.parent.glob("mcp.json.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        workflow.install_cursor_mcp(self.state, config=config)
        self.assertEqual(config.read_bytes(), installed)
        self.assertEqual(len(list(config.parent.glob("mcp.json.bak-*"))), 1)

    def test_install_refuses_invalid_json_without_changing_existing_file(self):
        config = self.root / "mcp.json"
        for original in (b'{ // JSONC comment\n}', b'{"mcpServers":[]}', b'[]'):
            config.write_bytes(original)
            with self.assertRaises(ValueError):
                workflow.install_cursor_mcp(self.state, config=config)
            self.assertEqual(config.read_bytes(), original)
        self.assertFalse((self.state / "mcp-token").exists())

    def test_insecure_endpoint_and_invalid_existing_token_are_rejected(self):
        for url in ("http://192.0.2.1/mcp", "http://localhost/not-mcp", "http://user:pass@localhost/mcp",
                    "http://localhost/mcp?token=secret", "file:///mcp"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                workflow.prepare_mcp(self.state, url)
        (self.state / "mcp-token").write_text("invalid", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "자동 교체하지"):
            workflow.prepare_mcp(self.state)
        self.assertEqual((self.state / "mcp-token").read_text(encoding="utf-8"), "invalid")

    def test_archived_release_can_prepare_install_and_serve_original_documents(self):
        repo = self.root / "release source"
        repo.mkdir()
        for folder in ("workflow", "docs", "templates", "scripts"):
            shutil.copytree(SOURCE / folder, repo / folder, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(SOURCE / "manifest.json", repo / "manifest.json")

        def git(*args):
            return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)

        git("init", "-b", "main")
        git("add", ".")
        git("-c", "user.name=Workflow Test", "-c", "user.email=test@example.invalid", "commit", "-m", "release fixture")
        state = self.root / "release runtime"
        active = workflow.sync(repo, state, offline=True)
        script = Path(active["snapshot"]) / "scripts/workflow.py"
        prepared = subprocess.run([sys.executable, str(script), "prepare-mcp", "--state-dir", str(state)],
                                  capture_output=True, timeout=10)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        token = (state / "mcp-token").read_text(encoding="utf-8").strip()
        self.assertNotIn(token, prepared.stdout.decode())
        config = self.root / "release cursor/mcp.json"
        installed = subprocess.run([sys.executable, str(script), "install-cursor-mcp", "--state-dir", str(state),
                                    "--transport", "stdio", "--config", str(config)], capture_output=True, timeout=10)
        self.assertEqual(installed.returncode, 0, installed.stderr.decode())
        settings = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]["ai-workflow"]
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "read_workflow_document", "arguments": {"commit": active["commit"], "path": "workflow/entry.md"}}}
        served = subprocess.run([settings["command"], *settings["args"]],
                                input=(json.dumps(message) + "\n").encode(), capture_output=True, timeout=10)
        self.assertEqual(served.returncode, 0, served.stderr.decode())
        result = json.loads(served.stdout)["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"])["text"],
                         (SOURCE / "workflow/entry.md").read_text(encoding="utf-8"))


class HTTPTests(MCPFixture):
    # Keep transport tests separate from the snapshot/configuration fixture tests.
    def setUp(self):
        super().setUp()
        self.token = "test-token-" + "x" * 40
        self.server = mcp.http_server(self.reader, self.token, port=0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, body=None, method="POST", headers=None, path="/mcp"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        defaults = {"Authorization": "Bearer " + self.token, "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"}
        defaults.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        try:
            connection.request(method, path, body=data, headers=defaults)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_http_handshake_status_entry_and_notification(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, body = self.request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(self.request({"jsonrpc": "2.0", "method": "notifications/initialized"}), (202, b""))
        for name, arguments in (("get_workflow_status", {}), ("read_workflow_document", {
                "commit": self.commit, "path": "workflow/entry.md"})):
            status, body = self.request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": name, "arguments": arguments}})
            self.assertEqual(status, 200)
            result = json.loads(body)["result"]
            self.assertFalse(result["isError"])
            self.assertTrue(json.loads(result["content"][0]["text"]))
        self.assertEqual(self.request(method="GET")[0], 405)
        self.assertEqual(self.request(method="DELETE")[0], 405)

    def test_http_auth_origin_protocol_size_and_path_boundaries(self):
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        for headers, expected in (({"Authorization": ""}, 401), ({"Authorization": "Bearer wrong"}, 401),
                                  ({"Origin": "https://evil.example"}, 403),
                                  ({"Origin": "http://localhost"}, 403),
                                  ({"MCP-Protocol-Version": "unsupported"}, 400),
                                  ({"Content-Type": "text/plain"}, 415), ({"Accept": "text/plain"}, 406)):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(ping, headers=headers)[0], expected)
        self.assertEqual(self.request({"oversized": "x" * mcp.MAX_REQUEST})[0], 413)
        self.assertEqual(self.request(ping, path="/mcp?token=secret")[0], 404)
        self.assertEqual(self.request([])[0], 200)
        self.assertEqual(self.request(ping)[0], 200)


if __name__ == "__main__":
    unittest.main()
