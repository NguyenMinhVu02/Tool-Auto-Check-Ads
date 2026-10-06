import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from apk_audit.web import AuditJobs, make_handler


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jobs = AuditJobs(self.root)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.jobs))
        self.addCleanup(self.server.server_close)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def request(self, path, body=None, filename=None, extra_headers=None):
        headers = {"X-Filename": filename} if filename else {}
        headers.update(extra_headers or {})
        request = Request(self.base + path, data=body, headers=headers)
        return urlopen(request, timeout=5)

    def test_page_and_upload_report_flow(self):
        page = self.request("/").read()
        self.assertIn(b'id="root"', page)
        self.assertIn(b'/app.js', page)
        self.assertIn(b'/app.css', page)
        self.assertIn(b'start-button', self.request('/app.js').read())

        def fake_run(archive, *, out, **kwargs):
            self.assertEqual(kwargs['engine'], 'codex')
            self.assertEqual(Path(archive).read_bytes(), b"fake archive")
            output = Path(out)
            output.mkdir(parents=True)
            report = {"output": str(output), "package": "demo.app", "warnings": [],
                      "summary": {"pass": 0, "fail": 0, "unknown": 1, "skipped": 0},
                      "findings": [{"rule_id": "DEMO", "status": "UNKNOWN", "title": "Demo", "area": "init"}]}
            (output / "report.json").write_text(json.dumps(report))
            return report

        with patch("apk_audit.web.run", side_effect=fake_run):
            response = self.request("/api/jobs", b"fake archive", "demo.apk")
            self.assertEqual(response.status, 202)
            job_id = json.load(response)["id"]
            for _ in range(50):
                job = json.load(self.request(f"/api/jobs/{job_id}"))
                if job["state"] == "done":
                    break
                time.sleep(0.02)
            self.assertEqual(job["state"], "done", job)
            report = json.load(self.request(f"/api/jobs/{job_id}/report"))
            self.assertEqual(report["package"], "demo.app")
            self.assertEqual(report["summary"]["unknown"], 1)

    def test_rejects_wrong_extension_and_empty_upload(self):
        with self.assertRaises(HTTPError) as wrong:
            self.request("/api/jobs", b"bytes", "../../bad.txt")
        self.assertEqual(wrong.exception.code, 400)
        with self.assertRaises(HTTPError) as empty:
            self.request("/api/jobs", b"", "app.apk")
        self.assertEqual(empty.exception.code, 413)

    def test_running_job_exposes_current_stage(self):
        reached_rules = threading.Event()
        finish = threading.Event()

        def fake_run(archive, *, out, progress, **kwargs):
            for stage in ("unpack", "facts", "rules"):
                progress(stage)
            reached_rules.set()
            self.assertTrue(finish.wait(5))
            progress("report")
            output = Path(out)
            output.mkdir(parents=True)
            report = {"output": str(output), "package": "demo.app", "warnings": [],
                      "summary": {"pass": 0, "fail": 0, "unknown": 0, "skipped": 0}, "findings": []}
            (output / "report.json").write_text(json.dumps(report))
            return report

        with patch("apk_audit.web.run", side_effect=fake_run):
            job_id = json.load(self.request("/api/jobs", b"fake archive", "demo.apk"))["id"]
            self.assertTrue(reached_rules.wait(5))
            job = json.load(self.request(f"/api/jobs/{job_id}"))
            self.assertEqual((job["state"], job["stage"]), ("running", "rules"))
            finish.set()
            for _ in range(50):
                job = json.load(self.request(f"/api/jobs/{job_id}"))
                if job["state"] == "done":
                    break
                time.sleep(0.02)
            self.assertEqual((job["state"], job["stage"]), ("done", "done"))

    def test_both_documents_reach_pipeline(self):
        ads = json.load(self.request(
            "/api/documents", b'{"inter_splash":"app-id"}', "ADS%20SCRIPTS.json",
            {"X-Document-Kind": "ads_scripts"},
        ))["id"]
        working = json.load(self.request(
            "/api/documents", b"key,value\npackage,demo.app\n", "working.csv",
            {"X-Document-Kind": "checklist"},
        ))["id"]

        def fake_run(archive, *, ads_scripts, checklist, out, **kwargs):
            self.assertEqual(json.loads(Path(ads_scripts).read_text())["inter_splash"], "app-id")
            self.assertIn("package,demo.app", Path(checklist).read_text())
            output = Path(out)
            output.mkdir(parents=True)
            report = {"output": str(output), "package": "demo.app", "warnings": [],
                      "summary": {"pass": 0, "fail": 0, "unknown": 1, "skipped": 0},
                      "findings": [], "docs_provided": {"ads_scripts": True, "checklist": True}}
            (output / "report.json").write_text(json.dumps(report))
            return report

        with patch("apk_audit.web.run", side_effect=fake_run):
            job_id = json.load(self.request(
                "/api/jobs", b"fake archive", "demo.apk",
                {"X-Ads-Scripts-Id": ads, "X-Checklist-Id": working},
            ))["id"]
            for _ in range(50):
                job = json.load(self.request(f"/api/jobs/{job_id}"))
                if job["state"] == "done":
                    break
                time.sleep(0.02)
            self.assertEqual(job["state"], "done", job)
            self.assertTrue(job["docs_used"])
            self.assertNotIn("documents", job)
            self.assertTrue(json.load(self.request(f"/api/jobs/{job_id}/report"))["docs_provided"]["checklist"])

    def test_one_document_cannot_be_attached_alone(self):
        ads = json.load(self.request(
            "/api/documents", b'{"key":"value"}', "ads.json",
            {"X-Document-Kind": "ads_scripts"},
        ))["id"]
        with self.assertRaises(HTTPError) as response:
            self.request("/api/jobs", b"fake archive", "demo.apk", {"X-Ads-Scripts-Id": ads})
        self.assertEqual(response.exception.code, 400)
        self.assertIn("Cần cả ADS SCRIPTS", response.exception.read().decode())


if __name__ == "__main__":
    unittest.main()
