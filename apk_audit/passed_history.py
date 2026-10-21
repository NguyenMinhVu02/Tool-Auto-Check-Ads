"""Remember which rules an app already passed, so later builds can skip opt-in rules.

Only rules that declare `skip_after_pass: true` use this. It trades re-verification for
tokens on purpose: a skipped rule says so explicitly and the user can force a full recheck.
"""
import json
from pathlib import Path
import time

from .utils import write_json


class PassedHistory:
    def __init__(self, directory):
        self.root = Path(directory) / 'passed'

    def _path(self, package):
        return self.root / (''.join(c if c.isalnum() or c in '._-' else '_' for c in package) + '.json')

    def _load(self, package):
        try:
            data = json.loads(self._path(package).read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def lookup(self, package, rule_id, apk_sha256):
        """Earlier PASS for this app from a different build, else None."""
        record = self._load(package).get(rule_id)
        if isinstance(record, dict) and record.get('apk_sha256') != apk_sha256:
            return record
        return None

    def record(self, report, build_id=None):
        """Store PASS verdicts of a finished live audit (never from a skipped/offline run)."""
        package = report.get('package')
        if not package or report.get('engine') == 'none':
            return 0
        data = self._load(package)
        stored = 0
        for finding in report.get('findings', []):
            if finding.get('status') == 'PASS' and finding.get('mode') == 'agent':
                data[finding['rule_id']] = {'apk_sha256': build_id or report.get('apk_sha256'),
                                            'version_name': report.get('version_name'),
                                            'engine': report.get('engine'), 'at': time.strftime('%Y-%m-%d %H:%M')}
                stored += 1
            elif finding.get('status') in {'FAIL', 'UNKNOWN'}:
                data.pop(finding['rule_id'], None)  # a later failure invalidates the old pass
        if stored or data != self._load(package):
            write_json(self._path(package), data)
        return stored

    def seed_from_reports(self, output_root):
        """Rebuild history from finished reports (e.g. after the cache directory was cleared)."""
        seeded = 0
        for path in sorted(Path(output_root).glob('*/report.json'), key=lambda p: p.stat().st_mtime):
            try:
                report = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(report, dict):
                    seeded += self.record(report)
            except (OSError, ValueError):
                continue
        return seeded
