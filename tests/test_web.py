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
        self.engine_detection = patch('apk_audit.web.detect_engines', return_value={
            'engines': [{'id': 'codex', 'label': 'Codex', 'installed': True},
                        {'id': 'claude', 'label': 'Claude', 'installed': True}], 'default': 'codex'})
        self.detect_engines = self.engine_detection.start()
        self.addCleanup(self.engine_detection.stop)
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
            self.assertEqual(Path(kwargs['cache_dir']), self.root / 'cache')
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

    def test_history_sanitizes_paths_and_explicit_resume_accepts_empty_body(self):
        job_id, archive = self.jobs.reserve('interrupted.apk')
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b'archive')
        self.jobs.update(job_id, state='running', upload_complete=True)
        restored = AuditJobs(self.root)
        self.server.RequestHandlerClass = make_handler(restored)
        history = json.load(self.request('/api/jobs'))['jobs']
        self.assertEqual(history[0]['id'], job_id)
        self.assertTrue(history[0]['resumable'])
        for key in ('documents', 'archive_path', 'output_path', 'report_path'):
            self.assertNotIn(key, history[0])
            self.assertNotIn(key, json.load(self.request(f'/api/jobs/{job_id}')))
        entered, finish = threading.Event(), threading.Event()
        def stop_run(*args, **kwargs):
            self.assertTrue(kwargs['resume'])
            entered.set()
            finish.wait(5)
            raise ValueError('test complete')
        with patch('apk_audit.web.run', side_effect=stop_run):
            try:
                response = self.request(f'/api/jobs/{job_id}/resume', b'')
                self.assertEqual(response.status, 202)
                self.assertTrue(entered.wait(2))
                with self.assertRaises(HTTPError) as busy:
                    self.request(f'/api/jobs/{job_id}/resume', b'')
                self.assertEqual(busy.exception.code, 409)
            finally:
                finish.set()
            for _ in range(50):
                if restored.active is None:
                    break
                time.sleep(.02)

    def test_rejects_wrong_extension_and_empty_upload(self):
        with self.assertRaises(HTTPError) as wrong:
            self.request("/api/jobs", b"bytes", "../../bad.txt")
        self.assertEqual(wrong.exception.code, 400)
        with self.assertRaises(HTTPError) as empty:
            self.request("/api/jobs", b"", "app.apk")
        self.assertEqual(empty.exception.code, 413)

    def test_engine_detection_endpoint_and_claude_default(self):
        self.detect_engines.return_value = {'engines': [
            {'id': 'codex', 'label': 'Codex', 'installed': False},
            {'id': 'claude', 'label': 'Claude', 'installed': True}], 'default': 'claude'}
        data = json.load(self.request('/api/engines'))
        self.assertEqual(data['default'], 'claude')
        job_id, _ = self.jobs.reserve('demo.apk')
        self.assertEqual(self.jobs.get(job_id)['engine'], 'claude')

    def test_selected_claude_reaches_pipeline_and_is_fixed_in_job(self):
        reached = threading.Event()
        finish = threading.Event()

        def fake_run(archive, *, engine, **kwargs):
            self.assertEqual(engine, 'claude')
            reached.set()
            finish.wait(5)
            raise ValueError('end test')

        with patch('apk_audit.web.run', side_effect=fake_run):
            job_id = json.load(self.request('/api/jobs', b'fake archive', 'demo.apk',
                                          {'X-Audit-Engine': 'claude'}))['id']
            try:
                self.assertTrue(reached.wait(5))
                self.assertEqual(json.load(self.request(f'/api/jobs/{job_id}'))['engine'], 'claude')
                self.detect_engines.return_value = {'engines': [], 'default': None}
                self.assertEqual(self.jobs.get(job_id)['engine'], 'claude')
            finally:
                finish.set()
            for _ in range(50):
                if self.jobs.get(job_id)['state'] == 'error':
                    break
                time.sleep(0.02)
            self.assertEqual(self.jobs.get(job_id)['state'], 'error')

    def test_invalid_or_missing_engine_rejected_before_consuming_documents(self):
        from io import BytesIO
        ads, _ = self.jobs.store_document('ads_scripts', 'ads.csv', BytesIO(b'a'), 1)
        working, _ = self.jobs.store_document('checklist', 'working.csv', BytesIO(b'b'), 1)
        for engine in ('claude;echo injected', 'none', ''):
            with self.subTest(engine=engine), self.assertRaises(HTTPError) as response:
                self.request('/api/jobs', b'bytes', 'demo.apk', {
                    'X-Audit-Engine': engine, 'X-Ads-Scripts-Id': ads, 'X-Checklist-Id': working})
            self.assertEqual(response.exception.code, 400)
        self.detect_engines.return_value = {'engines': [
            {'id': 'claude', 'installed': False}], 'default': None}
        for engine in ('claude', None):
            with self.subTest(engine=engine), self.assertRaises(ValueError):
                self.jobs.reserve('demo.apk', ads, working, engine)
        self.assertIsNone(self.jobs.active)
        self.assertEqual(set(self.jobs.documents), {ads, working})
        self.assertFalse((self.root / 'uploads').exists())

    def test_multi_sheet_documents_need_valid_sheet_choice(self):
        from io import BytesIO
        from unittest import mock
        with mock.patch('apk_audit.web.list_sheets', return_value=['App A', 'App B']):
            ads, sheets = self.jobs.store_document('ads_scripts', 'ads.xlsx', BytesIO(b'a'), 1)
            working, _ = self.jobs.store_document('checklist', 'working.xlsx', BytesIO(b'b'), 1)
        self.assertEqual(sheets, ['App A', 'App B'])
        for ads_sheet, checklist_sheet in ((None, 'App A'), ('App C', 'App A')):
            with self.subTest(ads_sheet=ads_sheet), self.assertRaisesRegex(ValueError, '(?i)sheet'):
                self.jobs.reserve('demo.apk', ads, working, 'claude', ads_sheet, checklist_sheet)
        self.assertEqual(set(self.jobs.documents), {ads, working})
        job_id, _ = self.jobs.reserve('demo.apk', ads, working, 'claude', 'App B', 'App B')
        self.assertEqual(self.jobs.get(job_id)['document_sheets'], {'ads_scripts': 'App B', 'checklist': 'App B'})

    def test_running_job_exposes_current_stage(self):
        reached_rules = threading.Event()
        finish = threading.Event()

        def fake_run(archive, *, out, progress, rule_progress, **kwargs):
            for stage in ("unpack", "facts", "rules"):
                progress(stage)
            rule_progress("start", {"index": 1, "total": 2, "completed": 0, "rule_id": "RULE_A", "title": "Rule A"})
            rule_progress("activity", {"rule_id": "RULE_A", "title": "Rule A", "phase": "initial", "attempt": 1, "allowance": 20, "tool_calls": 0, "command": None})
            for index in range(1, 9):
                rule_progress("activity", {"rule_id": "RULE_A", "title": "Rule A", "tool_calls": index, "command": f"rg ads{index}"})
            rule_progress("activity", {"rule_id": "UNKNOWN_RULE", "title": "X", "command": "ignored"})
            reached_rules.set()
            self.assertTrue(finish.wait(5))
            rule_progress("complete", {"index": 1, "total": 2, "completed": 1, "rule_id": "RULE_A", "title": "Rule A", "status": "FAIL", "from_cache": False})
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
            self.assertEqual((job["rule_completed"], job["rule_total"], job["current_rule"]), (0, 2, "RULE_A"))
            agent = job["current_rules"][0]
            self.assertEqual((agent["phase"], agent["tool_calls"], agent["allowance"], agent["command"]), ("initial", 8, 20, "rg ads8"))
            self.assertEqual(agent["recent_commands"], [f"rg ads{i}" for i in range(3, 9)])
            self.assertEqual(len(job["current_rules"]), 1)
            finish.set()
            for _ in range(50):
                job = json.load(self.request(f"/api/jobs/{job_id}"))
                if job["state"] == "done":
                    break
                time.sleep(0.02)
            self.assertEqual((job["state"], job["stage"]), ("done", "done"))
            self.assertEqual(job["last_rule"]["status"], "FAIL")

    def test_document_mismatch_waits_for_confirmation_then_runs_or_cancels(self):
        from apk_audit.preflight import DocumentMismatch
        calls = []

        def fake_run(archive, *, out, confirm_mismatch=False, **kwargs):
            calls.append(confirm_mismatch)
            if not confirm_mismatch:
                raise DocumentMismatch({"level": "block", "reasons": [{"code": "publisher", "message": "lệch tài khoản"}]})
            output = Path(out)
            output.mkdir(parents=True, exist_ok=True)
            report = {"output": str(output), "package": "demo.app", "warnings": [], "engine": "x",
                      "summary": {"pass": 0, "fail": 0, "unknown": 0, "skipped": 0}, "findings": []}
            (output / "report.json").write_text(json.dumps(report))
            return report

        def wait_for(job_id, states):
            for _ in range(100):
                job = json.load(self.request(f"/api/jobs/{job_id}"))
                if job["state"] in states:
                    return job
                time.sleep(0.02)
            self.fail(f"state stayed {job['state']}")

        with patch("apk_audit.web.run", side_effect=fake_run):
            job_id = json.load(self.request("/api/jobs", b"fake archive", "demo.apk"))["id"]
            job = wait_for(job_id, {"awaiting_confirmation"})
            self.assertEqual((job["stage"], job["preflight"]["reasons"][0]["code"]), ("preflight", "publisher"))
            self.assertIsNone(self.jobs.active)                       # no slot is held while the user decides
            self.assertEqual(json.load(self.request(f"/api/jobs/{job_id}/confirm", b"x"))["id"], job_id)
            self.assertEqual(wait_for(job_id, {"done", "error"})["state"], "done")
            self.assertEqual(calls, [False, True])
            second = json.load(self.request("/api/jobs", b"fake archive", "demo.apk"))["id"]
            wait_for(second, {"awaiting_confirmation"})
            self.request(f"/api/jobs/{second}/cancel", b"x")
            cancelled = wait_for(second, {"error"})
            self.assertIn("Đã hủy", cancelled["error"])
            with self.assertRaises(HTTPError) as response:
                self.request(f"/api/jobs/{second}/confirm", b"x")
            self.assertEqual(response.exception.code, 400)

    def test_bundled_vietnamese_fonts_are_served_and_csp_allows_canvas_favicon(self):
        for subset in ("latin", "latin-ext", "vietnamese"):
            response = self.request(f"/fonts/BeVietnamPro-{subset}-500.woff2")
            self.assertEqual((response.status, response.headers["Content-Type"]), (200, "font/woff2"))
            self.assertGreater(len(response.read()), 1000)
        policy = self.request("/").headers["Content-Security-Policy"]
        self.assertIn("img-src 'self' data:", policy)
        self.assertIn("font-src 'self'", policy)

    def test_html_report_and_id_csv_are_served_for_finished_jobs(self):
        marketing = {"documents_available": True, "id_problems": [{"screen": "Splash", "name": "inter_splash", "status": "Sai ID"}],
                     "screens": [{"title": "Màn Splash", "level": "issue", "flow_level": "ok", "flow_label": "Đạt", "id_issues": 1,
                                  "explanation": "<b>x</b>", "placements": [{"name": "inter_splash", "ad_type": "Inter", "status": "Sai ID: app khác ADS SCRIPTS",
                                                                           "document_id": "doc-1", "app_id": "app-1", "problem": True}]}]}

        def fake_run(archive, *, out, **kwargs):
            output = Path(out)
            output.mkdir(parents=True)
            report = {"output": str(output), "package": "demo.app", "warnings": [], "engine": "x",
                      "summary": {"pass": 0, "fail": 0, "unknown": 0, "skipped": 0}, "findings": [],
                      "marketing": marketing, "dev_view": {"groups": []}}
            (output / "report.json").write_text(json.dumps(report))
            return report

        with patch("apk_audit.web.run", side_effect=fake_run):
            job_id = json.load(self.request("/api/jobs", b"fake archive", "demo.apk"))["id"]
            for _ in range(100):
                if json.load(self.request(f"/api/jobs/{job_id}"))["state"] == "done":
                    break
                time.sleep(0.02)
        html = self.request(f"/api/jobs/{job_id}/report.html").read().decode()
        self.assertIn("1 ID ads đang có vấn đề", html)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertNotIn("<script", html)
        csv_text = self.request(f"/api/jobs/{job_id}/ids.csv").read().decode("utf-8-sig")
        self.assertIn("inter_splash,Inter,Sai ID: app khác ADS SCRIPTS,doc-1,app-1", csv_text)

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

    def test_invalid_csv_is_reported_at_documents_stage_before_jadx(self):
        from apk_audit.engines import NoneEngine
        ads_id = json.load(self.request('/api/documents', b'foo,bar\na,b\n', 'ads.csv',
                                        {'X-Document-Kind': 'ads_scripts'}))['id']
        working_id = json.load(self.request('/api/documents', b'key,value\npackage,demo.app\n', 'working.csv',
                                            {'X-Document-Kind': 'checklist'}))['id']
        with patch('apk_audit.pipeline.get_engine', return_value=NoneEngine()), patch('apk_audit.pipeline.prepare') as prepare:
            job_id = json.load(self.request('/api/jobs', b'not a real apk', 'demo.apk',
                {'X-Ads-Scripts-Id': ads_id, 'X-Checklist-Id': working_id}))['id']
            for _ in range(50):
                job = json.load(self.request(f'/api/jobs/{job_id}'))
                if job['state'] == 'error':
                    break
                time.sleep(0.02)
        self.assertEqual(job['state'], 'error')
        self.assertEqual(job['stage'], 'documents')
        self.assertIn('ADS SCRIPTS', job['error'])
        prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
