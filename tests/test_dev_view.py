import unittest

from apk_audit.dev_view import build_dev_view, parse_sections, rule_view


def finding(rule_id, status, reasoning='', reason='', evidence=None, claims=None):
    return {'rule_id': rule_id, 'title': rule_id.title(), 'status': status, 'reasoning': reasoning, 'reason': reason,
            'evidence': evidence or [], 'claims': claims or [], 'tool_calls': 3, 'mode': 'agent'}


class DevViewTests(unittest.TestCase):
    def test_sections_are_parsed_and_drafts_are_ignored(self):
        text = 'Kết luận: Sai.\nCần sửa: Làm idempotent\nvà hủy observer.\nĐã đúng: gate\n> Kết luận: nháp'
        self.assertEqual(parse_sections(text), {'Kết luận': 'Sai.', 'Cần sửa': 'Làm idempotent và hủy observer.', 'Đã đúng': 'gate'})

    def test_fail_shows_fix_and_only_violation_locations(self):
        evidence = [{'file': 'A.java', 'line': 10, 'excerpt': 'x'}, {'file': 'B.java', 'line': 20, 'excerpt': 'y'}]
        claims = [{'kind': 'compliance', 'evidence_indices': [0]}, {'kind': 'violation', 'evidence_indices': [1]}]
        view = rule_view(finding('R', 'FAIL', 'Kết luận: Lỗi.\nCần sửa: Sửa B.', evidence=evidence, claims=claims))
        self.assertEqual((view['status_label'], view['level'], view['fixes']), ('Cần sửa', 'issue', 'Sửa B.'))
        self.assertEqual(view['locations'], ['B.java:20'])

    def test_unknown_gets_plain_reason_and_pass_has_no_fix(self):
        unknown = rule_view(finding('R', 'UNKNOWN', 'Kết luận: UNKNOWN.', reason='unverified_evidence'))
        self.assertIn('dẫn chứng chưa khớp', unknown['unknown_reason'])
        ok = rule_view(finding('R', 'PASS', 'Kết luận: Tốt.\nCần sửa: Không xác định vi phạm.'))
        self.assertEqual((ok['status_label'], ok['fixes'], ok['locations']), ('Đạt', '', []))

    def test_groups_follow_screens_and_id_rule_points_to_marketing_table(self):
        findings = [finding('ADS_ID_SOURCE_AND_COVERAGE', 'FAIL', 'Kết luận: ID lệch.\nCần sửa: Đổi 12 ID...'),
                    finding('ADS_SPLASH_PLACEMENT', 'PASS'), finding('NEW_RULE', 'SKIPPED', reason='not_applicable_by_document')]
        view = build_dev_view(findings, {'id_problems': [{}] * 12})
        self.assertEqual([g['key'] for g in view['groups']], ['splash', 'config', 'other'])
        config = view['groups'][1]
        self.assertEqual(config['level'], 'issue')
        self.assertIn('12 ID sai/thiếu', config['rules'][0]['fixes'])
        self.assertEqual(view['groups'][2]['rules'][0]['status_label'], 'Không áp dụng')

    def test_guard_downgraded_unknown_shows_draft_leaning_not_boilerplate(self):
        text = ('Kết luận: UNKNOWN. Chưa đủ căn cứ để chấp nhận kết luận FAIL từ bản nháp AI.\n'
                'Lý do kiểm chứng: unverified_claims.\nBản nháp AI chưa được xác minh:\n'
                '> Kết luận: Observer đăng ký chồng.\n> Cần sửa: Hủy observer cũ.\n> Chưa xác minh: runtime')
        view = rule_view(finding('R', 'UNKNOWN', text, reason='unverified_claims'))
        self.assertTrue(view['conclusion'].startswith('AI nghiêng về kết luận có lỗi'))
        self.assertIn('Observer đăng ký chồng.', view['conclusion'])
        self.assertEqual((view['fixes'], view['unverified']), ('Hủy observer cũ.', 'runtime'))


if __name__ == '__main__':
    unittest.main()
