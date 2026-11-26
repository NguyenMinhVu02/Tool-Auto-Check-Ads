import io
import os
import tarfile
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from apk_audit import launcher, setup_tools


class SetupToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"APK_AUDIT_TOOLS_DIR": str(self.root / "tools")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_parse_java_major_handles_modern_and_legacy_output(self):
        self.assertEqual(setup_tools.parse_java_major('openjdk version "17.0.9" 2023-10-17'), 17)
        self.assertEqual(setup_tools.parse_java_major('java version "1.8.0_391"'), 8)
        self.assertEqual(setup_tools.parse_java_major('openjdk version "21" 2023-09-19'), 21)
        self.assertIsNone(setup_tools.parse_java_major("command not found"))

    def test_activate_prepends_portable_bin_dirs_and_sets_java_home(self):
        java_bin = self.root / "tools" / "jdk" / "jdk-17.0.9+9" / "bin"
        jadx_bin = self.root / "tools" / "jadx" / "bin"
        for directory, name in ((java_bin, "java"), (jadx_bin, "jadx")):
            directory.mkdir(parents=True)
            (directory / name).write_text("")
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}):
            setup_tools.activate()
            path = os.environ["PATH"].split(os.pathsep)
            self.assertIn(str(java_bin), path)
            self.assertIn(str(jadx_bin), path)
            self.assertEqual(path[-1], "/usr/bin")
            self.assertEqual(os.environ["JAVA_HOME"], str(java_bin.parent))
            setup_tools.activate()
            self.assertEqual(os.environ["PATH"].split(os.pathsep).count(str(java_bin)), 1)

    def test_extract_rejects_path_traversal(self):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../evil.txt", "x")
        with self.assertRaises(RuntimeError):
            setup_tools._extract(archive, self.root / "out", lambda _: None)
        self.assertFalse((self.root / "evil.txt").exists())

    def test_extract_tar_marks_bin_files_executable(self):
        archive = self.root / "tool.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            data = b"#!/bin/sh\n"
            info = tarfile.TarInfo("pkg/bin/tool")
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
        setup_tools._extract(archive, self.root / "out", lambda _: None)
        target = self.root / "out" / "pkg" / "bin" / "tool"
        if setup_tools.os_name() != "windows":
            self.assertTrue(os.access(target, os.X_OK))

    def test_download_rejects_checksum_mismatch(self):
        source = self.root / "payload.bin"
        source.write_bytes(b"hello")
        with self.assertRaises(RuntimeError):
            setup_tools._download(source.as_uri(), self.root / "copy.bin", lambda _: None, sha256="00" * 32)

    def test_setup_jobs_only_allows_known_tools_and_records_log(self):
        jobs = setup_tools.SetupJobs({"demo": lambda log: log("bước 1")})
        with self.assertRaises(ValueError):
            jobs.start("rm -rf /")
        job_id = jobs.start("demo")
        for _ in range(100):
            if jobs.get(job_id)["state"] != "running":
                break
            time.sleep(0.02)
        job = jobs.get(job_id)
        self.assertEqual(job["state"], "done")
        self.assertIn("bước 1", job["log"])

    def test_setup_jobs_reports_failure(self):
        def broken(log):
            raise RuntimeError("mất mạng")
        jobs = setup_tools.SetupJobs({"demo": broken})
        job_id = jobs.start("demo")
        for _ in range(100):
            if jobs.get(job_id)["state"] != "running":
                break
            time.sleep(0.02)
        self.assertEqual(jobs.get(job_id)["state"], "error")
        self.assertIn("mất mạng", jobs.get(job_id)["error"])

    def test_check_reports_required_tools(self):
        with mock.patch.object(setup_tools, "_which", return_value=None), \
                mock.patch("apk_audit.config.find_jadx", return_value=None):
            status = setup_tools.check()
        self.assertFalse(status["ready"])
        self.assertEqual(status["missing_required"], ["java", "jadx"])
        self.assertEqual({item["id"] for item in status["items"]}, {"java", "jadx", "node", "claude", "codex"})

    def test_login_rejects_unknown_engine(self):
        with self.assertRaises(ValueError):
            setup_tools.login("bash")

    @unittest.skipIf(setup_tools.os_name() == "windows", "shortcut file format differs on Windows")
    def test_create_shortcut_writes_launcher_into_desktop(self):
        desktop = self.root / "Desktop"
        with mock.patch.object(launcher.Path, "home", return_value=self.root), \
                mock.patch.object(launcher.shutil, "which", return_value=None), \
                mock.patch.object(launcher.subprocess, "run"):
            created = launcher.create_shortcut(desktop, uv="/opt/uv")
        self.assertTrue(created[0].is_file())
        self.assertTrue(str(created[0]).startswith(str(desktop)))
        content = created[0].read_text(encoding="utf-8")
        self.assertIn("/opt/uv", content)
        self.assertIn("serve", content)
        self.assertIn("--open", content)


if __name__ == "__main__":
    unittest.main()
