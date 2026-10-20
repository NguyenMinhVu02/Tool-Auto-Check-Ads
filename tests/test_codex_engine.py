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
assert args[args.index('--model') + 1] == 'gpt-6.1-sol'
assert args[args.index('--sandbox') + 1] == 'read-only'
assert 'model_reasoning_effort="medium"' in args
assert '--profile' not in args
assert '--ephemeral' in args and '--output-schema' in args
assert 'TEST_RULE' in sys.stdin.read()
schema = json.loads(Path(args[args.index('--output-schema') + 1]).read_text())
assert schema['properties']['evidence']['type'] == 'array'
assert 'claims' in schema['required']
assert 'path' in schema['properties']['claims']['items']['required']
Path(args[args.index('--output-last-message') + 1]).write_text(json.dumps({
    'rule_id': 'TEST_RULE', 'status': 'UNKNOWN', 'evidence': [],
    'reasoning': 'insufficient code', 'hint': 'sources/',
}))
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


if __name__ == "__main__":
    unittest.main()
