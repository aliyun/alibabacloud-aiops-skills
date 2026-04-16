# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from sysom_cli.lib.diagnosis_helper import _extract_get_diagnosis_result_payload


class ExtractGetDiagnosisResultTests(unittest.TestCase):
    def test_prefers_nonempty_result(self) -> None:
        d = {"status": "success", "result": {"io": 1}}
        self.assertEqual(_extract_get_diagnosis_result_payload(d), {"io": 1})

    def test_empty_result_uses_result_capital(self) -> None:
        d = {"status": "success", "result": {}, "Result": {"disk": 2}}
        self.assertEqual(_extract_get_diagnosis_result_payload(d), {"disk": 2})

    def test_fallback_sibling_keys(self) -> None:
        d = {
            "status": "success",
            "task_id": "t1",
            "iofsstat_payload": {"x": 3},
        }
        self.assertEqual(_extract_get_diagnosis_result_payload(d), {"x": 3})

    def test_multiple_non_meta_becomes_dict(self) -> None:
        d = {"status": "success", "a": 1, "b": 2}
        self.assertEqual(_extract_get_diagnosis_result_payload(d), {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()
