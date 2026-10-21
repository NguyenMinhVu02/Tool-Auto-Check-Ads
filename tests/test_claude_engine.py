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
assert '--print' in args and '--session-id' in args and '--no-session-persistence' not in args
assert args[args.index('--model') + 1] == 'claude-sonnet-5'
assert args[args.index('--effort') + 1] == 'low'
settings = json.loads(args[args.index('--settings') + 1])
assert settings['fallbackModel'] == []
assert settings['availableModels'] == ['claude-sonnet-5']
assert '--fallback-model' not in args
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

    def test_usage_from_cli_is_preserved(self):
        result = self.run_cli('''import json,sys
sys.stdin.read()
print(json.dumps({'type':'result','subtype':'success','usage':{'input_tokens':12,'output_tokens':3},'structured_output':{'rule_id':'TEST_RULE','status':'UNKNOWN','evidence':[],'claims':[],'reasoning':'missing flow','hint':'sources/'}}))
''')
        self.assertEqual(result.usage, {'input_tokens':12,'output_tokens':3})

    def test_error_after_tools_keeps_observed_count(self):
        with self.assertRaises(AuditError) as caught:
            self.run_cli('''import json,sys
sys.stdin.read()
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':'read-1','name':'Read'}]}}), flush=True)
print(json.dumps({'type':'result','subtype':'error','is_error':True}), flush=True)
''')
        self.assertEqual(caught.exception.tool_calls, 1)

    def test_timeout_after_tools_keeps_observed_count(self):
        with self.assertRaises(AuditError) as caught:
            self.run_cli('''import json,sys,time
sys.stdin.read()
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':'read-1','name':'Read'}]}}), flush=True)
time.sleep(5)
''', timeout=0.15)
        self.assertEqual(caught.exception.tool_calls, 1)

    def test_budget_exhaustion_never_returns_a_verdict(self):
        result = self.run_cli('''import json, sys
sys.stdin.read()
for i in range(3):
 print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':str(i),'name':'Read'}]}}), flush=True)
''', budget=1)
        self.assertTrue(result.exhausted_budget)
        self.assertEqual(result.text, '')

    def test_budget_stop_keeps_completed_tool_result_for_followup(self):
        result = self.run_cli('''import json,sys
sys.stdin.read()
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':'r1','name':'Read','input':{'file_path':'Flow.java'}}]}}), flush=True)
print(json.dumps({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'r1','content':'if (enabled) load();'}]}}), flush=True)
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':'r2','name':'Read'}]}}), flush=True)
''', budget=1)
        self.assertTrue(result.exhausted_budget)
        self.assertEqual(result.events[0]['type'], 'source_read')
        self.assertIn('if (enabled)', result.events[0]['output'])

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
