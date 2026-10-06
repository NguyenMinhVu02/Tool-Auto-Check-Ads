import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apk_audit.engines import CodexEngine


class CodexEngineTests(unittest.TestCase):
    def test_cli_uses_luna_read_only_and_returns_structured_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / "codex"
            executable.write_text('''#!/usr/bin/env python3
import json
from pathlib import Path
import sys
args = sys.argv[1:]
assert args[args.index('--model') + 1] == 'gpt-6-luna'
assert args[args.index('--sandbox') + 1] == 'read-only'
assert '--ephemeral' in args and '--output-schema' in args
assert 'TEST_RULE' in sys.stdin.read()
schema = json.loads(Path(args[args.index('--output-schema') + 1]).read_text())
assert schema['properties']['evidence']['type'] == 'array'
Path(args[args.index('--output-last-message') + 1]).write_text(json.dumps({
    'rule_id': 'TEST_RULE', 'status': 'UNKNOWN', 'evidence': [],
    'reasoning': 'insufficient code', 'hint': 'sources/',
}))
print(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution'}}), flush=True)
''')
            executable.chmod(0o755)
            tools = type("FakeTools", (), {"root": root})()
            with patch.dict(os.environ, {"PATH": f"{root}:{os.environ['PATH']}"}):
                result = CodexEngine().run_agent('{"rule_id":"TEST_RULE"}', tools, 2, timeout=5)
            self.assertEqual(json.loads(result.text)["status"], "UNKNOWN")
            self.assertEqual(result.tool_calls, 1)


if __name__ == "__main__":
    unittest.main()
