import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow", SOURCE / "scripts/workflow.py")
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.PIPE,
    ).decode().strip()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "source with spaces"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        (self.repo / "workflow").mkdir()
        (self.repo / "templates").mkdir()
        (self.repo / "scripts").mkdir()
        (self.repo / "manifest.json").write_text(json.dumps({
            "schema_version": 1, "entry": "workflow/entry.md",
            "revision": "2026-11-08", "layout_version": 5,
        }), encoding="utf-8")
        (self.repo / "workflow/entry.md").write_text("first version\n", encoding="utf-8")
        (self.repo / "scripts/workflow.py").write_text("# fixture\n", encoding="utf-8")
        (self.repo / "templates/entry-instructions.md").write_bytes(
            (SOURCE / "templates/entry-instructions.md").read_bytes())
        self.first = self.commit()
        self.remote = self.root / "remote.git"
        git(self.root, "clone", "--bare", str(self.repo), str(self.remote))
        git(self.repo, "remote", "add", "origin", str(self.remote))
        self.state = self.root / "runtime with spaces"

    def commit(self):
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Workflow Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", "test: fixture")
        return git(self.repo, "rev-parse", "HEAD")

    def sync(self, offline=False):
        return workflow.sync(self.repo, self.state, offline=offline)

    def test_remote_sync_ignores_dirty_checkout_and_preserves_it(self):
        dirty = self.repo / "workflow/entry.md"
        dirty.write_text("uncommitted draft\n", encoding="utf-8")
        active = self.sync()
        self.assertEqual(active["commit"], self.first)
        self.assertEqual(Path(active["entry"]).read_text(encoding="utf-8"), "first version\n")
        self.assertEqual(dirty.read_text(encoding="utf-8"), "uncommitted draft\n")
        self.assertIsNotNone(active["remote_checked_at"])

    def test_new_remote_commit_retains_previous_snapshot(self):
        old = self.sync()
        (self.repo / "workflow/entry.md").write_text("second version\n", encoding="utf-8")
        second = self.commit()
        git(self.repo, "push", "origin", "main")
        new = self.sync()
        self.assertEqual(new["commit"], second)
        self.assertEqual(Path(old["entry"]).read_text(encoding="utf-8"), "first version\n")
        self.assertEqual(Path(new["entry"]).read_text(encoding="utf-8"), "second version\n")

    def test_offline_explicitly_marks_no_remote_check(self):
        active = self.sync(offline=True)
        self.assertEqual(active["source"], "local-head")
        self.assertIsNone(active["remote_checked_at"])
        status = json.loads((self.state / "sync-status.json").read_text(encoding="utf-8"))
        self.assertFalse(status["remote_checked"])

    def test_failed_fetch_preserves_active_and_reports_failure(self):
        self.sync()
        before = (self.state / "active.json").read_bytes()
        git(self.repo, "remote", "set-url", "origin", str(self.root / "missing.git"))
        with self.assertRaises(RuntimeError):
            self.sync()
        self.assertEqual((self.state / "active.json").read_bytes(), before)
        self.assertFalse(json.loads((self.state / "sync-status.json").read_text(encoding="utf-8"))["ok"])

    def test_modified_snapshot_is_not_silently_overwritten(self):
        active = self.sync()
        Path(active["entry"]).write_text("changed locally\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "스냅샷이 변경"):
            self.sync()
        self.assertEqual(Path(active["entry"]).read_text(encoding="utf-8"), "changed locally\n")

    def test_invalid_release_does_not_replace_active(self):
        self.sync()
        before = (self.state / "active.json").read_bytes()
        (self.repo / "manifest.json").write_text('{"schema_version": 99}', encoding="utf-8")
        self.commit()
        git(self.repo, "push", "origin", "main")
        with self.assertRaisesRegex(RuntimeError, "manifest"):
            self.sync()
        self.assertEqual((self.state / "active.json").read_bytes(), before)

    def test_symlink_release_is_rejected(self):
        try:
            (self.repo / "outside.md").symlink_to("../outside.md")
        except OSError:
            self.skipTest("symlinks unavailable on this host")
        self.commit()
        with self.assertRaisesRegex(RuntimeError, "배포할 수 없는 경로"):
            self.sync(offline=True)
        self.assertFalse((self.state / "active.json").exists())

    def test_existing_lock_prevents_second_writer(self):
        with workflow.exclusive(self.state):
            with self.assertRaisesRegex(RuntimeError, "잠금"):
                self.sync()
        self.assertFalse((self.state / ".sync-lock").exists())

    def test_codex_install_preserves_user_rules_and_is_idempotent(self):
        self.sync()
        home = self.root / "codex home"
        home.mkdir()
        path = home / "AGENTS.md"
        original = "# Personal rules\r\nKeep my text.\r\n".encode()
        path.write_bytes(original)
        workflow.install_codex(self.state, "bash", home)
        installed = path.read_bytes()
        self.assertTrue(installed.startswith(original))
        backups = list(home.glob("AGENTS.md.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        workflow.install_codex(self.state, "bash", home)
        self.assertEqual(path.read_bytes(), installed)
        self.assertEqual(len(list(home.glob("AGENTS.md.bak-*"))), 1)

    def test_override_and_legacy_instructions_require_manual_review(self):
        self.sync()
        home = self.root / "codex"
        home.mkdir()
        (home / "AGENTS.override.md").write_text("override", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "override"):
            workflow.install_codex(self.state, "bash", home)
        (home / "AGENTS.override.md").unlink()
        original = "# 단계별 에이전트 운영\nexisting rules\n"
        (home / "AGENTS.md").write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "전체 워크플로우"):
            workflow.install_codex(self.state, "bash", home)
        self.assertEqual((home / "AGENTS.md").read_text(encoding="utf-8"), original)

    def test_malformed_marker_is_rejected(self):
        for text in (workflow.END + workflow.BEGIN, workflow.BEGIN,
                     workflow.BEGIN + workflow.END + workflow.BEGIN + workflow.END):
            with self.assertRaises(RuntimeError):
                workflow.merge_instructions(text, workflow.BEGIN + "new" + workflow.END)

    def test_template_paths_are_environment_specific_and_quoted(self):
        self.sync()
        text = workflow.render(self.state, "bash")
        self.assertNotIn("{{", text)
        self.assertIn(str(self.state / "active.json"), text)
        self.assertIn("'", text)
        text = workflow.render(self.state, "powershell")
        self.assertIn("& '", text)
        self.assertEqual(workflow.command_text(["a'b", "x y"], "powershell"), "& 'a''b' 'x y'")


if __name__ == "__main__":
    unittest.main()
