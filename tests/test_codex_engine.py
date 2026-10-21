import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apk_audit.engines import CodexEngine


class CodexEngineTests(unittest.TestCase):
    def test_budget_stop_preserves_bounded_completed_reads_for_followup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / 'codex'
            executable.write_text('''#!/usr/bin/env python3
import json, sys
sys.stdin.read()
print(json.dumps({'type':'item.started','item':{'type':'command_execution'}}), flush=True)
print(json.dumps({'type':'item.completed','item':{'type':'command_execution','command':'read Flow.java','aggregated_output':'source line\\n' * 2000}}), flush=True)
print(json.dumps({'type':'item.started','item':{'type':'command_execution'}}), flush=True)
''')
            executable.chmod(0o755)
            tools = type('Tools', (), {'root': root})()
            with patch.dict(os.environ, {'PATH': f"{root}:{os.environ['PATH']}"}):
                result = CodexEngine().run_agent('TEST_RULE', tools, 1, timeout=5)
            self.assertTrue(result.exhausted_budget)
            self.assertEqual(result.text, '')
            reads = [e for e in result.events if e.get('type') == 'source_read']
            self.assertEqual(reads[0]['command'], 'read Flow.java')
            self.assertLessEqual(len(reads[0]['output']), 6000)

    def test_cli_pins_sol_medium_read_only_and_returns_structured_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / "codex"
            executable.write_text('''#!/usr/bin/env python3
import json
from pathlib import Path
import sys
args = sys.argv[1:]
assert args[args.index('--model') + 1] == 'gpt-6-sol'
assert args[args.index('--sandbox') + 1] == 'read-only'
assert 'model_reasoning_effort="low"' in args
assert '--profile' not in args
assert '--ephemeral' not in args and '--output-schema' in args  # sessions persist so repairs can resume
assert 'skills.include_instructions=false' in args and 'project_doc_max_bytes=0' in args
assert 'features.plugins=false' in args and '--ignore-rules' in args
assert args[-1] == '-'
assert 'TEST_RULE' in sys.stdin.read()
schema = json.loads(Path(args[args.index('--output-schema') + 1]).read_text())
assert schema['properties']['evidence']['type'] == 'array'
assert 'claims' in schema['required']
assert 'path' in schema['properties']['claims']['items']['required']
Path(args[args.index('--output-last-message') + 1]).write_text(json.dumps({
    'rule_id': 'TEST_RULE', 'status': 'UNKNOWN', 'evidence': [],
    'reasoning': 'insufficient code', 'hint': 'sources/',
}))
print(json.dumps({'type': 'thread.started', 'thread_id': 'abc-123'}), flush=True)
print(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution'}}), flush=True)
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 7, 'output_tokens': 2}}), flush=True)
''')
            executable.chmod(0o755)
            tools = type("FakeTools", (), {"root": root})()
            with patch.dict(os.environ, {"PATH": f"{root}:{os.environ['PATH']}"}):
                result = CodexEngine().run_agent('{"rule_id":"TEST_RULE"}', tools, 2, timeout=5)
            self.assertEqual(json.loads(result.text)["status"], "UNKNOWN")
            self.assertEqual(result.tool_calls, 1)
            self.assertEqual(result.usage, {'input_tokens': 7, 'output_tokens': 2})
            self.assertEqual(result.session_id, 'abc-123')
            self.assertFalse([e for e in result.events if e.get('type') == 'thread.started'])

    def test_quota_error_from_json_stream_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / 'codex'
            executable.write_text('''#!/usr/bin/env python3
import json, sys
sys.stdin.read()
print(json.dumps({'type':'error','message':"You've hit your usage limit. Try again at 7:10 PM."}), flush=True)
print(json.dumps({'type':'turn.failed','error':{'message':"You've hit your usage limit. Try again at 7:10 PM."}}), flush=True)
sys.exit(1)
''')
            executable.chmod(0o755)
            tools = type('Tools', (), {'root': root})()
            with patch.dict(os.environ, {'PATH': f"{root}:{os.environ['PATH']}"}):
                with self.assertRaisesRegex(Exception, 'usage limit.*7:10 PM'):
                    CodexEngine().run_agent('TEST_RULE', tools, 2, timeout=5)

    def test_resume_continues_session_read_only_from_workspace_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / 'codex'
            executable.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
assert args[:3] == ['exec', 'resume', 'abc-123'], args
assert 'sandbox_mode="read-only"' in args and '--sandbox' not in args and '--cd' not in args
assert '--output-schema' in args and 'skills.include_instructions=false' in args and args[-1] == '-'
assert Path(os.getcwd()).resolve() == Path(sys.argv[0]).resolve().parent
assert 'FOLLOWUP' in sys.stdin.read()
Path(args[args.index('--output-last-message') + 1]).write_text(json.dumps({'rule_id': 'R', 'status': 'UNKNOWN'}))
print(json.dumps({'type': 'thread.started', 'thread_id': 'abc-123'}), flush=True)
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'output_tokens': 1}}), flush=True)
''')
            executable.chmod(0o755)
            tools = type('Tools', (), {'root': root})()
            with patch.dict(os.environ, {'PATH': f"{root}:{os.environ['PATH']}"}):
                result = CodexEngine().run_agent('FOLLOWUP', tools, 2, timeout=5, resume='abc-123')
            self.assertEqual((result.session_id, result.usage['input_tokens']), ('abc-123', 3))
            home = root / 'home' / 'sessions' / '2026' / '10'
            home.mkdir(parents=True)
            keep, drop = home / 'rollout-1-other.jsonl', home / 'rollout-2-abc-123.jsonl'
            keep.write_text('x'); drop.write_text('x')
            with patch.dict(os.environ, {'CODEX_HOME': str(root / 'home')}):
                CodexEngine.close_session('abc-123')
            self.assertTrue(keep.exists())
            self.assertFalse(drop.exists())


if __name__ == "__main__":
    unittest.main()
