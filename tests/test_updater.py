import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from apk_audit import updater


def make_zip(version, extra=b"new"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        prefix = f"apk-audit-{version}/"
        bundle.writestr(prefix + "pyproject.toml", f'[project]\nname = "apk-audit"\nversion = "{version}"\n')
        bundle.writestr(prefix + "apk_audit/__init__.py", extra)
        bundle.writestr(prefix + "rulepacks/default/pack.yaml", "version: new\n")
        info = zipfile.ZipInfo(prefix + "installer/cai-dat-linux.sh")
        info.external_attr = 0o755 << 16
        bundle.writestr(info, "#!/bin/bash\n")
    return buffer.getvalue()


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "pyproject.toml").write_text('[project]\nname = "apk-audit"\nversion = "0.2.0"\n')
        (self.root / "apk_audit").mkdir()
        (self.root / "apk_audit" / "__init__.py").write_text("old")
        (self.root / "out").mkdir()
        (self.root / "out" / "report.json").write_text("keep")

    def release(self, version, payload, digest=True):
        source = self.root.parent / f"rel-{version}-{id(payload)}.zip"
        source.write_bytes(payload)
        self.addCleanup(source.unlink)
        asset = {"name": f"apk-audit-{version}.zip", "browser_download_url": source.as_uri()}
        if digest:
            asset["digest"] = "sha256:" + hashlib.sha256(payload).hexdigest()
        return {"tag_name": f"v{version}", "body": "Ghi chú", "html_url": "https://example", "assets": [asset]}

    def test_version_compare(self):
        self.assertGreater(updater.parse_version("v0.10.0"), updater.parse_version("0.9.9"))
        self.assertEqual(updater.parse_version("0.2.0"), (0, 2, 0))

    def test_check_reports_newer_release(self):
        release = self.release("0.3.0", make_zip("0.3.0"))
        result = updater.Updater(self.root, fetch=lambda: release).check()
        self.assertTrue(result["available"])
        self.assertEqual((result["current"], result["latest"]), ("0.2.0", "0.3.0"))

    def test_check_same_version_is_not_available(self):
        release = self.release("0.2.0", make_zip("0.2.0"))
        self.assertFalse(updater.Updater(self.root, fetch=lambda: release).check()["available"])

    def test_private_repo_error_is_explained(self):
        def fail():
            raise updater.urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        result = updater.Updater(self.root, fetch=fail).check()
        self.assertFalse(result["available"])
        self.assertIn("riêng tư", result["error"])

    def test_apply_replaces_shipped_files_and_keeps_results(self):
        release = self.release("0.3.0", make_zip("0.3.0"))
        done = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(updater.subprocess, "run", return_value=done), \
                mock.patch("apk_audit.launcher.create_shortcut"):
            version = updater.Updater(self.root, fetch=lambda: release).apply(lambda _: None)
        self.assertEqual(version, "0.3.0")
        self.assertEqual((self.root / "apk_audit" / "__init__.py").read_text(), "new")
        self.assertEqual(updater.current_version(self.root), "0.3.0")
        self.assertEqual((self.root / "out" / "report.json").read_text(), "keep")
        self.assertFalse((self.root / ".update").exists())

    def test_checksum_mismatch_keeps_old_version(self):
        release = self.release("0.3.0", make_zip("0.3.0"))
        release["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(RuntimeError):
            updater.Updater(self.root, fetch=lambda: release).apply(lambda _: None)
        self.assertEqual((self.root / "apk_audit" / "__init__.py").read_text(), "old")

    def test_failed_dependency_sync_restores_old_version(self):
        release = self.release("0.3.0", make_zip("0.3.0"))
        failed = mock.Mock(returncode=1, stdout="", stderr="boom")
        with mock.patch.object(updater.subprocess, "run", return_value=failed):
            with self.assertRaises(RuntimeError):
                updater.Updater(self.root, fetch=lambda: release).apply(lambda _: None)
        self.assertEqual((self.root / "apk_audit" / "__init__.py").read_text(), "old")
        self.assertEqual(updater.current_version(self.root), "0.2.0")

    def test_git_checkout_and_busy_server_refuse_update(self):
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            updater.Updater(self.root, fetch=dict).start()
        (self.root / ".git").rmdir()
        with self.assertRaises(RuntimeError):
            updater.Updater(self.root, fetch=dict, busy=lambda: True).start()


if __name__ == "__main__":
    unittest.main()
