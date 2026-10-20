import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from apk_audit.web import AuditJobs


class JobPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        detection = patch('apk_audit.web.detect_engines', return_value={
            'engines': [{'id': 'codex', 'installed': True}], 'default': 'codex'})
        detection.start()
        self.addCleanup(detection.stop)
        self.jobs = AuditJobs(self.root, workers=2)

    def reserve_archive(self, documents=False):
        ids = []
        if documents:
            for kind in ('ads_scripts', 'checklist'):
                ids.append(self.jobs.store_document(kind, 'doc.json', io.BytesIO(b'{}'), 2)[0])
        job_id, archive = self.jobs.reserve('app.apk', *ids)
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(b'archive')
        return job_id, archive

    def test_xlsx_upload_keeps_style_and_documents_survive_restart(self):
        from openpyxl import Workbook
        from openpyxl.styles import Font
        from apk_audit.documents import load_document
        book = Workbook()
        sheet = book.active
        sheet.append(['Ads type', 'Name', 'ID'])
        sheet.append(['open', 'open_resume', 'id-open'])
        sheet['C2'].font = Font(strike=True)
        content = io.BytesIO()
        book.save(content)
        raw = content.getvalue()
        ads, _ = self.jobs.store_document('ads_scripts', 'ads.xlsx', io.BytesIO(raw), len(raw))
        working, _ = self.jobs.store_document('checklist', 'working.csv', io.BytesIO(b'key,value\n'), 10)
        job_id, archive = self.jobs.reserve('app.apk', ads, working)
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(b'archive')
        self.jobs.update(job_id, upload_complete=True, state='running')
        restored = AuditJobs(self.root)
        doc = load_document(restored.get(job_id)['documents']['ads_scripts'], 'ads_scripts')
        self.assertEqual(doc['placements'][0]['state'], 'disabled')
        self.assertTrue(restored.get(job_id)['resumable'])

    def wait_terminal(self, jobs, job_id):
        for _ in range(100):
            job = jobs.get(job_id)
            if job['state'] in {'done', 'error'}:
                return job
            time.sleep(.01)
        self.fail('job did not finish')

    def fake_run(self, archive, *, out, ads_scripts, checklist, workers, **kwargs):
        self.assertIsInstance(archive, Path)
        self.assertEqual(workers, 2)
        for document in (ads_scripts, checklist):
            if document is not None:
                self.assertIsInstance(document, Path)
                self.assertEqual(document.read_text(), '{}')
        out.mkdir(exist_ok=True)
        report = {'output': str(out), 'package': 'demo', 'warnings': [], 'summary': {}, 'findings': []}
        (out / 'report.json').write_text(json.dumps(report))
        return report

    def test_done_job_and_report_survive_restart(self):
        job_id, archive = self.reserve_archive()
        with patch('apk_audit.web.run', side_effect=self.fake_run):
            self.jobs.start(job_id, archive)
            self.assertEqual(self.wait_terminal(self.jobs, job_id)['state'], 'done')
        restored = AuditJobs(self.root)
        self.assertEqual(restored.get(job_id)['state'], 'done')
        self.assertEqual(json.loads(restored.read_report(job_id))['package'], 'demo')
        self.assertEqual(restored.list_jobs()[0]['id'], job_id)
        self.assertNotIn('archive_path', restored.list_jobs()[0])
        self.assertIsNone(restored.active)

    def test_interrupted_job_waits_for_explicit_resume_and_preserves_documents(self):
        job_id, archive = self.reserve_archive(documents=True)
        self.jobs.update(job_id, state='running', upload_complete=True, stage='rules')
        with patch('apk_audit.web.run', side_effect=self.fake_run) as runner:
            restored = AuditJobs(self.root, workers=2)
            self.assertFalse(runner.called)
            job = restored.get(job_id)
            self.assertEqual(job['state'], 'error')
            self.assertTrue(job['resumable'])
            self.assertTrue(job['interrupted'])
            restored.resume(job_id)
            self.assertEqual(self.wait_terminal(restored, job_id)['state'], 'done')
        self.assertEqual(len(restored.get(job_id)['documents']), 2)
        with self.assertRaises(ValueError):
            restored.resume(job_id)

    def test_incomplete_upload_never_resumes_even_if_partial_file_exists(self):
        job_id, _ = self.reserve_archive()
        restored = AuditJobs(self.root)
        self.assertFalse(restored.get(job_id)['resumable'])
        with self.assertRaises(ValueError):
            restored.resume(job_id)
        self.assertIsNone(restored.active)

    def test_malformed_metadata_ignored_without_blocking_good_history(self):
        job_id, _ = self.reserve_archive()
        (self.root / 'jobs' / ('a' * 32 + '.json')).write_text('{')
        (self.root / 'jobs' / ('b' * 32 + '.json')).write_text('[]')
        restored = AuditJobs(self.root)
        self.assertEqual([job['id'] for job in restored.list_jobs()], [job_id])

    def test_resume_rejects_escaped_symlink_or_wrong_extension_paths(self):
        for tamper in ('archive_path', 'documents', 'output_path', 'report_path', 'symlink', 'extension'):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as temp:
                jobs = AuditJobs(temp)
                job_id, archive = jobs.reserve('app.apk')
                archive.parent.mkdir(parents=True, exist_ok=True)
                archive.write_bytes(b'archive')
                jobs.update(job_id, state='running', upload_complete=True)
                meta = Path(temp) / 'jobs' / f'{job_id}.json'
                data = json.loads(meta.read_text())
                if tamper == 'symlink':
                    archive.unlink()
                    archive.symlink_to('/etc/passwd')
                elif tamper == 'extension':
                    changed = archive.with_suffix('.txt')
                    archive.rename(changed)
                    data['archive_path'] = str(changed)
                elif tamper == 'documents':
                    data['documents'] = {'ads_scripts': '/etc/passwd', 'checklist': '/etc/passwd'}
                else:
                    data[tamper] = '/etc/passwd'
                meta.write_text(json.dumps(data))
                restored = AuditJobs(temp)
                with self.assertRaises((ValueError, KeyError)):
                    restored.resume(job_id)
                self.assertIsNone(restored.active)

    def test_resume_is_exclusive_and_old_completion_cannot_unlock_new_job(self):
        job_id, _ = self.reserve_archive()
        self.jobs.update(job_id, state='running', upload_complete=True)
        restored = AuditJobs(self.root)
        entered, finish = threading.Event(), threading.Event()
        def blocked(*args, **kwargs):
            entered.set()
            finish.wait(5)
            return self.fake_run(*args, **kwargs)
        with patch('apk_audit.web.run', side_effect=blocked):
            restored.workers = 2
            restored.resume(job_id)
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(RuntimeError):
                    restored.resume(job_id)
                with self.assertRaises(RuntimeError):
                    restored.reserve('second.apk')
            finally:
                finish.set()
            self.assertEqual(self.wait_terminal(restored, job_id)['state'], 'done')
        new_id, _ = restored.reserve('second.apk')
        restored.update(job_id, state='done')
        self.assertEqual(restored.active, new_id)

    def test_metadata_extra_fields_are_not_exposed_and_bad_sort_key_is_ignored(self):
        job_id, _ = self.reserve_archive()
        meta = self.root / 'jobs' / f'{job_id}.json'
        data = json.loads(meta.read_text())
        data['private_extra'] = '/sensitive/file'
        meta.write_text(json.dumps(data))
        restored = AuditJobs(self.root)
        self.assertNotIn('private_extra', restored.list_jobs()[0])
        data['created_at'] = []
        meta.write_text(json.dumps(data))
        self.assertEqual(AuditJobs(self.root).list_jobs(), [])

    def test_missing_documents_and_late_symlink_are_not_resumable(self):
        job_id, archive = self.reserve_archive(documents=True)
        self.jobs.update(job_id, state='running', upload_complete=True)
        restored = AuditJobs(self.root)
        archive.unlink()
        archive.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            restored.resume(job_id)
        archive.unlink()
        archive.write_bytes(b'archive')
        Path(self.jobs.get(job_id)['documents']['checklist']).unlink()
        recovered = AuditJobs(self.root)
        self.assertFalse(recovered.get(job_id)['resumable'])
        with self.assertRaises(ValueError):
            recovered.resume(job_id)

    def test_report_is_revalidated_after_symlink_tampering(self):
        job_id, archive = self.reserve_archive()
        with patch('apk_audit.web.run', side_effect=self.fake_run):
            self.jobs.start(job_id, archive)
            self.wait_terminal(self.jobs, job_id)
        report = self.root / job_id / 'report.json'
        report.unlink()
        report.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            self.jobs.read_report(job_id)
