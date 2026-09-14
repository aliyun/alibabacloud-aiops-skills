"""Offline regression checks for the document-reference evaluation contract."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import validate_evals as validator


class EvalValidationTests(unittest.TestCase):
    def setUp(self):
        validator.errors.clear()
        self.filename = 'route-18-ops-rerun-task-instance.jsonc'
        self.case = json.loads((validator.EVALS_DIR / self.filename).read_text())['evals']

    def validate(self, case):
        validator.check_skill_paths(self.filename, case)
        validator.check_assertions(self.filename, case)
        validator.check_offline_contract(self.filename, case)

    def test_file_reference_passes_without_final_answer_keywords(self):
        self.assertNotIn('result_verification', self.case)
        self.validate(self.case)
        self.assertEqual(validator.errors, [])
        value = self.case['expectations'][0]['value']
        for record in [f'Read("/workspace/{value}")', f'cat {value}', f'[指导文档]({value})']:
            self.assertIn(value, record)
        self.assertNotIn(value, '仅引用 references/ops/pause-task-instance/SKILL.md')

    def test_missing_or_overbroad_reference_is_rejected(self):
        for value in ['references/missing/SKILL.md', 'references/ops/', 'SKILL.md', '']:
            validator.errors.clear()
            case = copy.deepcopy(self.case)
            case['expectations'][0]['value'] = value
            self.validate(case)
            self.assertTrue(validator.errors, value)

    def test_reference_outside_suite_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'suite'
            (root / 'references').mkdir(parents=True)
            (Path(temporary) / 'outside.md').write_text('outside')
            case = copy.deepcopy(self.case)
            case['expectations'][0]['value'] = 'references/../../outside.md'
            with mock.patch.object(validator, 'ROOT', root):
                self.validate(case)
            self.assertTrue(validator.errors)

    def test_real_execution_and_mock_dependency_are_rejected(self):
        for rule in [{'type': 'shell_interaction', 'id': 'cli-version-gate', 'command_pattern': 'aliyun version'},
                     {'type': 'mock_action', 'id': 'retry', 'mock_id': 'm-error'}]:
            validator.errors.clear()
            case = copy.deepcopy(self.case)
            case['expectations'].append(rule)
            self.validate(case)
            self.assertTrue(validator.errors)

    def test_response_wording_and_unscoped_credential_rules_are_rejected(self):
        for mutate in [lambda case: case.update(result_verification={'checks': [{'name': 'hitl-confirmation'}]}),
                       lambda case: case['forbidden'][0].pop('target')]:
            validator.errors.clear()
            case = copy.deepcopy(self.case)
            mutate(case)
            self.validate(case)
            self.assertTrue(validator.errors)

    def test_all_cases_have_valid_specific_targets_and_unique_identity(self):
        cases = validator.load_cases()
        self.assertEqual(len(cases), 83)
        validator.check_uniqueness(cases)
        for filename, case in cases:
            validator.check_name_matches_file(filename, case)
            validator.check_skill_paths(filename, case)
            validator.check_assertions(filename, case)
            validator.check_offline_contract(filename, case)
            self.assertNotIn('mocks', case)
            for expectation in case['expectations']:
                self.assertTrue((validator.ROOT / expectation['value']).is_file())
        self.assertEqual(validator.errors, [])

    def test_version_scenarios_match_current_api_index(self):
        index = json.loads((validator.ROOT / 'references/config/openapi-2.0-versions.json').read_text())
        versions = {api['name']: api['min_version'] for api in index['apis']}
        for api in ['ListProjects', 'GetProject']:
            self.assertEqual(versions[api], '6.0')
        for api in ['CreateBasicProject', 'CreateDevProdProject', 'UpdateBasicProject', 'UpdateDevProdProject', 'DeleteProject']:
            self.assertEqual(versions[api], '6.3')
        self.assertEqual(versions['CreateDataset'], '6.2')
        for path in validator.EVALS_DIR.glob('gate-standalone-*.jsonc'):
            case = json.loads(path.read_text())['evals']
            refs = {e['value'] for e in case['expectations']}
            self.assertIn('references/config/openapi-2.0-versions.json', refs)
            self.assertIn('references/version-aware-openapi.md', refs)
            if 'project-query-' in path.name:
                self.assertIn('references/dataplan/create-project/SKILL.md', refs)

    def test_error_scenarios_have_fixed_response_samples(self):
        observed = set()
        for filename, case in validator.load_cases():
            category = validator.error_category(filename)
            if category:
                observed.add(category)
                self.assertIn(validator.ERROR_CODES[category], case['prompt'])
                self.assertIn('不是本次请求结果', case['prompt'])
                self.assertNotIn('mock_action', json.dumps(case))
        self.assertEqual(observed, set(validator.ERROR_CODES))


if __name__ == '__main__':
    unittest.main(verbosity=2)
