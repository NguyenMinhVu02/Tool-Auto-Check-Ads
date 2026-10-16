import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apk_audit.engines import ClaudeEngine, detect_engines
from apk_audit.errors import AuditError


class ClaudeEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = type('Tools', (), {'root': self.root})()

    def run_cli(self, script, budget=3, timeout=5):
        cli = self.root / 'claude'
        cli.write_text('#!/usr/bin/env python3\n' + script)
        cli.chmod(0o755)
        with patch.dict(os.environ, {'PATH': f"{self.root}:{os.environ['PATH']}"}):
            return ClaudeEngine().run_agent('TEST_RULE', self.tools, budget, timeout)

    def test_uses_read_tools_and_schema_and_counts_tool_ids_once(self):
        result = self.run_cli('''import json, sys
from pathlib import Path
args = sys.argv[1:]
assert '--print' in args and '--no-session-persistence' in args
assert '--restricted' in args and '--safe-mode' in args
assert args[args.index('--tools') + 1] == 'Read,Glob,Grep'
assert args[args.index('--permission-mode') + 1] == 'dontAsk'
assert args[args.index('--output-format') + 1] == 'stream-json'
assert '--strict-mcp-config' in args
assert json.loads(args[args.index('--json-schema') + 1])['properties']['evidence']['type'] == 'array'
assert 'TEST_RULE' in sys.stdin.read()
event = {'type': 'assistant', 'message': {'content': [{'type':'tool_use','id':'read-1','name':'Read'}]}}
print(json.dumps(event), flush=True)
print(json.dumps(event), flush=True)
print(json.dumps({'type':'result','subtype':'success','is_error':False,'structured_output':{
    'rule_id':'TEST_RULE','status':'UNKNOWN','evidence':[], 'reasoning':'missing flow','hint':'sources/'}}), flush=True)
''')
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(json.loads(result.text)['rule_id'], 'TEST_RULE')

    def test_budget_exhaustion_never_returns_a_verdict(self):
        result = self.run_cli('''import json, sys
sys.stdin.read()
for i in range(3):
 print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':str(i),'name':'Read'}]}}), flush=True)
''', budget=1)
        self.assertTrue(result.exhausted_budget)
        self.assertEqual(result.text, '')

    def test_timeout_stops_cli(self):
        with self.assertRaisesRegex(AuditError, 'quá thời gian'):
            self.run_cli('import sys,time\nsys.stdin.read()\ntime.sleep(5)\n', timeout=0.1)

    def test_cli_error_and_missing_result_are_explicit(self):
        with self.assertRaisesRegex(AuditError, 'Claude CLI'):
            self.run_cli('import sys\nsys.stdin.read()\nprint("login required", file=sys.stderr)\nsys.exit(1)\n')
        with self.assertRaisesRegex(AuditError, 'kết quả'):
            self.run_cli('import sys\nsys.stdin.read()\n')

    def test_error_result_with_zero_exit_is_not_a_verdict(self):
        with self.assertRaisesRegex(AuditError, 'Claude CLI'):
            self.run_cli('import json,sys\nsys.stdin.read()\nprint(json.dumps({"type":"result","is_error":True,"subtype":"error_max_turns"}))\n')

    def test_auth_failure_on_stdout_is_explained(self):
        with self.assertRaisesRegex(AuditError, 'OAuth session expired'):
            self.run_cli('import json,sys\nsys.stdin.read()\nprint(json.dumps({"type":"result","subtype":"success","result":"Failed to authenticate: OAuth session expired"}))\nsys.exit(1)\n')

    def test_detection_selects_claude_if_codex_missing(self):
        with patch('apk_audit.engines.shutil.which', side_effect=lambda name: '/bin/claude' if name == 'claude' else None):
            data = detect_engines()
        self.assertEqual(data['default'], 'claude')
        self.assertEqual([item['id'] for item in data['engines'] if item['installed']], ['claude'])

    def test_detection_without_installed_cli_has_no_default(self):
        with patch('apk_audit.engines.shutil.which', return_value=None):
            self.assertIsNone(detect_engines()['default'])
