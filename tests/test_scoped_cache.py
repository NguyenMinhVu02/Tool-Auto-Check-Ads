from pathlib import Path
import tempfile
import unittest

from apk_audit.contracts import Finding
from apk_audit.scoped_cache import dependency_paths, hash_dependencies


def trace_for(*commands):
    return {'attempts': [{'events': [{'type': 'source_read', 'command': c} for c in commands]}]}


class ScopedCacheTests(unittest.TestCase):
    finding = Finding('R', 'T', 'agent', evidence=[{'file': 'sources/a/A.java', 'line': 1, 'excerpt': 'x'}])

    def test_paths_from_shell_codex_and_claude_absolute_reads(self):
        paths = dependency_paths(self.finding, trace_for(
            "/bin/bash -lc \"nl -ba sources/a/B.java | sed -n '1,9p'; cat resources/assets/ad_config.json\"",
            'Read {"file_path": "/work/run-1/sources/a/C.java"}', 'pwd'))
        self.assertEqual(paths, ['resources/assets/ad_config.json', 'sources/a/A.java', 'sources/a/B.java', 'sources/a/C.java'])

    def test_unlistable_dependencies_disable_reuse(self):
        self.assertIsNone(dependency_paths(self.finding, trace_for('rg -n loadNative')))            # workspace-wide search
        self.assertIsNone(dependency_paths(self.finding, trace_for('x ' * 600 + 'sources/a/B.java')))  # truncated command
        self.assertIsNone(dependency_paths(self.finding, {'attempts': []}))
        self.assertIsNone(dependency_paths(self.finding, {'attempts': [{'error': 'boom', 'events': []}]}))

    def test_hashes_cover_files_directories_and_globs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'sources/a').mkdir(parents=True)
            (root / 'sources/a/A.java').write_text('one')
            before = hash_dependencies(root, ['sources/a', 'sources/a/A.java'])
            (root / 'sources/a/A.java').write_text('two')
            after = hash_dependencies(root, ['sources/a', 'sources/a/A.java'])
            self.assertNotEqual(before['sources/a'], after['sources/a'])
            self.assertNotEqual(before['sources/a/A.java'], after['sources/a/A.java'])
            glob_before = hash_dependencies(root, ['sources/a/*.java'])['sources/a/*.java']
            (root / 'sources/a/B.java').write_text('new')
            self.assertNotEqual(glob_before, hash_dependencies(root, ['sources/a/*.java'])['sources/a/*.java'])
            self.assertIsNone(hash_dependencies(root, ['sources/../*.java']))
            self.assertIsNone(hash_dependencies(root, ['../outside']))


if __name__ == '__main__':
    unittest.main()
