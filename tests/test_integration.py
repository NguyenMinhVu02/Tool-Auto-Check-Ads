import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_framework import FrameworkTests
from apk_audit.contracts import AgentResult, Rule
from apk_audit.engines import ReplayEngine
from apk_audit.agent import evaluate
from apk_audit.tools import WorkspaceTools
from apk_audit.rules.engine import evaluate_static
from apk_audit import run
from apk_audit.errors import AuditError


class IntegrationTests(unittest.TestCase):
    setUp = FrameworkTests.setUp
    agent_rule = FrameworkTests.agent_rule
    # Reuse the isolated workspace fixture without duplicating inherited tests.
    def test_pipeline_reports_its_real_stages(self):
        stages = []
        run(self.ws, rules=self.pack, out=self.root/'out', engine='none', progress=stages.append)
        self.assertEqual(stages, ['unpack', 'facts', 'rules', 'report'])

    def test_cache_replays_and_invalidates_when_context_changes(self):
        (self.pack / 'rules/a.yaml').write_text('''- id: EXAMPLE
  title: Example
  mode: agent
  question: Inspect
  verdict: {pass_when: yes, fail_when: no, unknown_when: unclear}
''')
        # Quote YAML verdicts because yes/no otherwise become booleans.
        (self.pack / 'rules/a.yaml').write_text((self.pack / 'rules/a.yaml').read_text().replace('pass_when: yes, fail_when: no', 'pass_when: "yes", fail_when: "no"'))
        response = json.dumps({'rule_id':'EXAMPLE','status':'FAIL','evidence':[{'file':'sources/demo/App.java','line':4,'excerpt':'Example.init();'}]})
        kwargs = dict(rules=self.pack, out=self.root/'out', cache_dir=self.root/'cache', trace=True)
        first = run(self.ws, engine=ReplayEngine([response]), **kwargs)
        second = run(self.ws, engine=ReplayEngine([]), **kwargs)
        self.assertEqual(first['summary']['fail'], 1)
        self.assertEqual(second['summary']['fail'], 1)
        self.assertEqual(second['summary']['from_cache'], 1)
        self.assertTrue((self.root/'out/trace/EXAMPLE.json').exists())
        (self.pack/'context.md').write_text('new context')
        third = run(self.ws, engine=ReplayEngine([json.dumps({'rule_id':'EXAMPLE','status':'UNKNOWN'})]), **kwargs)
        self.assertEqual(third['summary']['from_cache'], 0)
        self.assertEqual(third['summary']['unknown'], 1)

    def test_budget_exhaustion(self):
        finding, _ = evaluate(self.agent_rule(), WorkspaceTools(self.ws), ReplayEngine([AgentResult('{"rule_id":"EXAMPLE","status":"PASS"}', tool_calls=26)]), '')
        self.assertEqual(finding.status, 'UNKNOWN')
        self.assertTrue(finding.exhausted_budget)

    def test_all_static_check_types(self):
        facts = {'manifest': {'meta_data': {'flag': 'on'}, 'activities':[{'name':'demo.Main'}]}, 'assets':{'json':{'config.json':{'enabled':False,'list':[{'id':'abc'}]}}}, 'strings':{'candidates':{'token':[{'value':'abc'}]},'sdk_versions':{'sdk':'2.10.0'}}}
        cases = [
            ('manifest_meta', {'key':'flag','equals':'on'}, 'PASS'),
            ('manifest_has', {'collection':'activities','name':'demo.Main'}, 'PASS'),
            ('string_present', {'key':'token','equals':'abc'}, 'PASS'),
            ('string_absent', {'key':'token','equals':'abc'}, 'FAIL'),
            ('asset_json_path', {'file':'config.json','path':'enabled'}, 'PASS'),
            ('asset_json_match', {'file':'config.json','path':'list[0].id','regex':'a.*'}, 'PASS'),
            ('sdk_version', {'key':'sdk','min':'2.9'}, 'PASS'),
        ]
        for check, params, expected in cases:
            with self.subTest(check=check):
                finding = evaluate_static(Rule('X', 'X', 'static', check=check, params=params), facts)
                self.assertEqual(finding.status, expected)

    def test_cli_fail_exit_and_invalid_input(self):
        (self.pack/'rules/a.yaml').write_text('- id: X\n  title: mismatch\n  mode: static\n  check: manifest_meta\n  params: {key: sample, equals: other}\n')
        command = [sys.executable, '-m', 'apk_audit', str(self.ws), '--rules', str(self.pack), '--out', str(self.root/'out')]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        bad = subprocess.run([sys.executable, '-m', 'apk_audit', '/does/not/exist'], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)

    def test_missing_codex_cli_is_explicit(self):
        with patch('apk_audit.engines.shutil.which', return_value=None):
            with self.assertRaises(AuditError) as context:
                run(self.ws, engine='codex', out=self.root/'out')
        self.assertEqual(context.exception.code, 6)

    def test_default_engine_uses_codex_for_agent_rules(self):
        (self.pack/'rules/a.yaml').write_text('''- id: EXAMPLE
  title: Example
  mode: agent
  question: Inspect
  verdict: {pass_when: "yes", fail_when: "no", unknown_when: unclear}
''')
        response = json.dumps({'rule_id': 'EXAMPLE', 'status': 'PASS', 'evidence': [
            {'file': 'sources/demo/App.java', 'line': 4, 'excerpt': 'Example.init();'}]})
        fake = ReplayEngine([response])
        fake.name = 'codex:gpt-6-luna'
        with patch('apk_audit.pipeline.get_engine', return_value=fake) as get_engine:
            report = run(self.ws, rules=self.pack, out=self.root/'out', cache_dir=self.root/'cache')
        get_engine.assert_called_once_with('codex')
        self.assertEqual(report['summary']['pass'], 1)

    def test_mcp_stdio(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        async def check():
            transport = StdioTransport(command=sys.executable, args=['-m','apk_audit','mcp','--workspace',str(self.ws)])
            async with Client(transport) as client:
                tools = await client.list_tools()
                self.assertEqual(len(tools), 9)
                result = await client.call_tool('read_lines', {'file':'sources/demo/App.java','start':4,'end':4})
                self.assertFalse(result.is_error)
                self.assertIn('Example.init', str(result.content))
        asyncio.run(asyncio.wait_for(check(), timeout=20))


del FrameworkTests
