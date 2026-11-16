import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_docs', ROOT / 'scripts/check_docs.py')
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


class ReadingTests(unittest.TestCase):
    def test_default_environment_paths_exclude_foreign_profiles_and_optional_rules(self):
        for env, other in (('codex', 'cursor'), ('cursor', 'codex')):
            for role in ('계획', '실행', '통합', '총괄', '사용자검증', '커밋목록'):
                with self.subTest(environment=env, role=role):
                    report = docs.reading_report(ROOT, env, role)
                    paths = report['files']
                    self.assertIn(f'workflow/models-{env}.md', paths)
                    self.assertNotIn(f'workflow/models-{other}.md', paths)
                    self.assertNotIn('workflow/models-codex-limit.md', paths)
                    for path in ('records-layout', 'migration', 'access-mcp', 'quality-rust'):
                        self.assertNotIn(f'workflow/{path}.md', paths)
                    self.assertIsNone(report['tokens'])

    def test_condition_paths_include_prerequisites_without_double_counting(self):
        report = docs.reading_report(ROOT, 'cursor', '실행', ['rust', 'code', 'quality', 'mcp', 'rust'])
        for name in ('quality', 'quality-code', 'quality-rust', 'access-mcp'):
            self.assertIn(f'workflow/{name}.md', report['files'])
        self.assertGreater(report['duplicate_references'], 0)
        self.assertEqual(report['characters'], sum(report['files'].values()))
        self.assertEqual(report['conditions'].count('rust'), 1)
        report = docs.reading_report(ROOT, 'codex', '계획', ['migration'])
        self.assertIn('workflow/records-layout.md', report['files'])
        self.assertIn('workflow/migration.md', report['files'])

    def test_resume_only_excludes_explicitly_retained_unchanged_documents(self):
        first = docs.reading_report(ROOT, 'codex', '실행')
        retained = ['workflow/common.md', 'workflow/models-codex.md']
        resumed = docs.reading_report(ROOT, 'codex', '실행', retained=retained)
        self.assertEqual(resumed['characters'], first['characters'])
        self.assertEqual(resumed['read_characters'], first['characters'] - sum(first['files'][p] for p in retained))
        full = docs.reading_report(ROOT, 'codex', '실행', retained=first['files'])
        self.assertEqual(full['read_characters'], 0)
        with self.assertRaises(ValueError):
            docs.reading_report(ROOT, 'codex', '실행', retained=['workflow/migration.md'])

    def test_status_and_test_query_do_not_require_models_or_all_work_items(self):
        basic = docs.reading_report(ROOT, 'cursor', '상태 조회')
        self.assertEqual(set(basic['files']), {'workflow/entry.md', 'workflow/common.md', 'workflow/status.md'})
        detailed = docs.reading_report(ROOT, 'cursor', '상태 조회', ['tests'])
        self.assertEqual(set(detailed['files']) - set(basic['files']), {'workflow/records-evidence.md'})

    def test_invalid_conditions_do_not_silently_increase_read_scope(self):
        for env, role, conditions in [('cursor', '실행', ['codex-limit']),
                                      ('codex', '커밋목록', ['migration']),
                                      ('codex', '실행', ['unknown'])]:
            with self.subTest(conditions=conditions), self.assertRaises(ValueError):
                docs.reading_report(ROOT, env, role, conditions)

    def test_json_report_exposes_limits_and_returns_errors(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = docs.check(ROOT, 'cursor', '실행', ['rust'], as_json=True)
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0, report['errors'])
        self.assertEqual(len(report['reports']), 1)
        self.assertIn('인계·모델 출력·추론', report['reports'][0]['excluded'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(docs.check(ROOT, 'codex', 'missing', as_json=True), 1)

    def test_legacy_role_table_measures_full_bodies_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'workflow').mkdir()
            (root / 'manifest.json').write_text('{"schema_version":1,"entry":"workflow/entry.md"}', encoding='utf-8')
            entry = '| 실행 | [a](a.md), [a](a.md), [b](b.md) |\n'
            (root / 'workflow/entry.md').write_text(entry, encoding='utf-8')
            (root / 'workflow/a.md').write_text('한글\n', encoding='utf-8')
            (root / 'workflow/b.md').write_text('abc', encoding='utf-8')
            report = docs.reading_report(root, 'codex', '실행')
            self.assertEqual(report['characters'], len(entry) + 6)
            self.assertEqual(report['duplicate_references'], 1)

    def test_missing_environment_profile_is_not_treated_as_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'workflow').mkdir()
            shutil.copyfile(ROOT / 'manifest.json', root / 'manifest.json')
            text = (ROOT / 'workflow/entry.md').read_text(encoding='utf-8')
            text = '\n'.join(line for line in text.splitlines() if not line.startswith('| cursor |'))
            (root / 'workflow/entry.md').write_text(text, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '환경 프로필'):
                docs.reading_policy(root)


class LinkTests(unittest.TestCase):
    def test_all_repository_document_links_and_anchors(self):
        self.assertEqual(docs.validate(ROOT), [])

    def test_broken_fragment_in_readme_and_nested_examples_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'README.md').write_text('[bad](#absent)\n# Present\n', encoding='utf-8')
            (root / 'AGENTS.md').write_text('# Rules\n', encoding='utf-8')
            (root / 'examples/nested').mkdir(parents=True)
            (root / 'examples/nested/sample.md').write_text('[missing](gone.md)\n', encoding='utf-8')
            errors = docs.validate(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any('README.md' in error for error in errors))
            self.assertTrue(any('gone.md' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
