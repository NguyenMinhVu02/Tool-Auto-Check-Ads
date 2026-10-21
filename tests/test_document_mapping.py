import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from apk_audit.documents import load_document
from apk_audit.errors import AuditError
from apk_audit.contracts import AgentResult
from apk_audit.document_structure import ai_mapper, mapping_schema
from apk_audit.engines import CodexEngine, ClaudeEngine


class DocumentMappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def csv(self, text):
        path = self.root / 'document.csv'
        path.write_text(text, encoding='utf-8-sig')
        return path

    def mapping(self, **overrides):
        return {'decision': 'mapped', 'sheet': 'CSV', 'header_line': 2,
                'columns': [{'field': 'ads type', 'column': 0},
                            {'field': 'name', 'column': 1}, {'field': 'id', 'column': 2}],
                **overrides}

    def test_common_aliases_and_delimiters_need_no_ai(self):
        for delimiter in (',', ';', '\t', '|'):
            with self.subTest(delimiter=delimiter):
                path = self.csv('Partner documents\n' + delimiter.join(['Loại quảng cáo', 'Vị trí', 'Ad Unit ID']) +
                                '\n' + delimiter.join(['native', 'native_first', 'exact-id']) + '\n')
                mapper = Mock(side_effect=AssertionError('AI should not be used'))
                doc = load_document(path, 'ads_scripts', mapper=mapper)
                self.assertEqual(doc['placements'][0]['id'], 'exact-id')
                self.assertEqual(doc['placements'][0]['line'], 3)
                self.assertEqual(doc['parsing']['method'], 'deterministic')
                mapper.assert_not_called()

    def test_alternative_description_columns_keep_their_own_values(self):
        path = self.csv('Ads type,Name,ID,Mô tả,Description\n'
                        'native,native_first,id-1,Mô tả tiếng Việt,English description\n')
        placement = load_document(path, 'ads_scripts')['placements'][0]
        self.assertEqual(placement['description'], 'Mô tả tiếng Việt')
        self.assertEqual(placement['description_en'], 'English description')

    def test_ai_only_maps_columns_and_values_come_from_original_csv(self):
        path = self.csv('Partner documents,,\nKind of unit,Screen code,Production unit\n'
                        'native,native_first,exact-ID-CaSe\n')
        mapper = Mock(return_value=self.mapping())
        doc = load_document(path, 'ads_scripts', mapper=mapper)
        self.assertEqual(doc['placements'][0]['id'], 'exact-ID-CaSe')
        self.assertEqual(doc['placements'][0]['line'], 3)
        self.assertEqual(doc['parsing']['method'], 'ai_mapping')
        mapper.assert_called_once()
        self.assertEqual(mapper.call_args.args[0]['kind'], 'ads_scripts')

    def test_untrusted_mapping_cannot_point_outside_preview_or_reuse_columns(self):
        path = self.csv('Title,,\nKind of unit,Screen code,Production unit\nnative,native_first,id-1\n')
        invalid = [self.mapping(sheet='invented'), self.mapping(header_line=99),
                   self.mapping(header_line=True),
                   dict(decision='ambiguous', sheet='CSV', header_line=2, columns=[]),
                   dict(decision='mapped', sheet='CSV', header_line=2,
                        columns=[{'field': 'ads type', 'column': 0}, {'field': 'name', 'column': 1},
                                 {'field': 'id', 'column': 1}]),
                   dict(decision='mapped', sheet='CSV', header_line=2,
                        columns=[{'field': 'ads type', 'column': 0}, {'field': 'name', 'column': 1},
                                 {'field': 'id', 'column': 10}])]
        for output in invalid:
            with self.subTest(output=output):
                with self.assertRaises(AuditError):
                    load_document(path, 'ads_scripts', mapper=lambda _: output)

    def test_ai_working_mapping_preserves_task_detail_and_source_line(self):
        path = self.csv('Checklist\nRequirement,Expected setting\nPackage name,demo.app\n')
        mapper = lambda _: dict(decision='mapped', sheet='CSV', header_line=2,
                               columns=[{'field': 'task', 'column': 0}, {'field': 'task detail', 'column': 1}])
        doc = load_document(path, 'checklist', mapper=mapper)
        self.assertEqual(doc['checklist_rows'][0]['detail'], 'demo.app')
        self.assertEqual(doc['checklist_rows'][0]['line'], 3)

    def test_ai_xlsx_mapping_retains_original_strike_and_fill(self):
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Custom ads'
        sheet.append(['Partner documents'])
        sheet.append(['Kind of unit', 'Screen code', 'Production unit'])
        sheet.append(['open', 'open_resume', 'exact-id'])
        sheet['C3'].fill = PatternFill('solid', fgColor='FFFF00')
        path = self.root / 'document.xlsx'
        workbook.save(path)
        doc = load_document(path, 'ads_scripts', mapper=lambda _: self.mapping(sheet='Custom ads'))
        self.assertEqual(doc['placements'][0]['state'], 'disabled')
        self.assertEqual(doc['placements'][0]['id'], 'exact-id')
        self.assertEqual(doc['sheet'], 'Custom ads')

    def test_multiple_app_sheets_are_never_silently_chosen_by_ai(self):
        from openpyxl import Workbook
        workbook = Workbook()
        for sheet in (workbook.active, workbook.create_sheet('Another app')):
            sheet.append(['Ads type', 'Name', 'ID'])
            sheet.append(['native', 'native_first', 'id-1'])
        path = self.root / 'apps.xlsx'
        workbook.save(path)
        mapper = Mock(side_effect=AssertionError('Do not guess target app'))
        with self.assertRaisesRegex(AuditError, 'nhiều sheet'):
            load_document(path, 'ads_scripts', mapper=mapper)
        mapper.assert_not_called()

    def test_native_cli_mapping_uses_mapping_schema_and_pinned_model(self):
        from types import SimpleNamespace
        for name, engine in [('codex', CodexEngine()), ('claude', ClaudeEngine())]:
            with self.subTest(engine=name):
                script = self.root / name
                script.write_text('''#!/usr/bin/env python3
import sys,json
from pathlib import Path
args=sys.argv[1:]
instruction=sys.stdin.read()
assert 'MAP_COLUMNS_ONLY' in instruction
assert 'workspace jadx' not in instruction
payload={'decision':'mapped','sheet':'CSV','header_line':2,'columns':[]}
if '--output-schema' in args:
 assert args[args.index('--model')+1]=='gpt-6-sol'
 schema=json.loads(Path(args[args.index('--output-schema')+1]).read_text())
 assert 'columns' in schema['required'] and 'evidence' not in schema['properties']
 assert 'features.shell_tool=false' in args
 Path(args[args.index('--output-last-message')+1]).write_text(json.dumps(payload))
 print(json.dumps({'type':'turn.completed','usage':{'input_tokens':15}}))
else:
 assert args[args.index('--model')+1]=='claude-sonnet-5'
 assert args[args.index('--tools')+1]==''
 schema=json.loads(args[args.index('--json-schema')+1])
 assert 'columns' in schema['required'] and 'evidence' not in schema['properties']
 print(json.dumps({'type':'result','subtype':'success','structured_output':payload,'usage':{'input_tokens':15}}))
''')
                script.chmod(0o755)
                with patch.dict(os.environ, {'PATH': f"{self.root}:{os.environ['PATH']}"}):
                    result = engine.map_document('MAP_COLUMNS_ONLY', SimpleNamespace(root=self.root),
                                                 mapping_schema(), timeout=5)
                self.assertEqual(json.loads(result.text)['sheet'], 'CSV')
                self.assertEqual(result.tool_calls, 0)
                self.assertEqual(result.usage['input_tokens'], 15)

    def test_ai_fallback_is_bounded_and_exposes_usage_without_raw_document(self):
        adapter = Mock(name='adapter')
        adapter.name = 'codex:test'
        adapter.map_document.return_value = AgentResult(json.dumps(self.mapping()), usage={'input_tokens': 17})
        metrics = []
        path = self.csv('Title,,\nKind of unit,Screen code,Production unit\nnative,native_first,exact-id\n')
        doc = load_document(path, 'ads_scripts', mapper=ai_mapper(adapter, metrics))
        self.assertEqual(doc['placements'][0]['id'], 'exact-id')
        adapter.map_document.assert_called_once()
        self.assertEqual(adapter.map_document.call_args.kwargs['timeout'], 90)
        self.assertEqual(metrics[0]['usage']['input_tokens'], 17)
        self.assertNotIn('exact-id', json.dumps(metrics))
        adapter.map_document.return_value = AgentResult('{}', tool_calls=1)
        with self.assertRaises(AuditError):
            load_document(path, 'ads_scripts', mapper=ai_mapper(adapter, []))

    def test_pipeline_automatically_uses_selected_engine_for_document_mapping(self):
        from apk_audit.pipeline import run
        from apk_audit.engines import ReplayEngine
        workspace = self.root / 'workspace'
        (workspace / 'sources').mkdir(parents=True)
        path = self.csv('Title,,\nKind of unit,Screen code,Production unit\nnative,native_first,id-1\n')
        engine = ReplayEngine([])
        engine.map_document = Mock(return_value=AgentResult(json.dumps(self.mapping()), usage={'input_tokens': 7}))
        report = run(workspace, engine=engine, ads_scripts=path, out=self.root / 'out',
                     cache_dir=self.root / 'cache')
        self.assertEqual(report['metrics']['documents']['parsed'][0]['method'], 'ai_mapping')
        self.assertEqual(report['metrics']['documents']['ai_attempts'][0]['usage']['input_tokens'], 7)
        engine.map_document.assert_called_once()
