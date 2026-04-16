# -*- coding: utf-8 -*-
"""memory --deep-diagnosis 本地入口信封形状；gomemdump 移除与 Go→memgraph 归类。"""
from __future__ import annotations

import copy
import unittest
from argparse import Namespace
from unittest.mock import patch

from sysom_cli.lib.diagnosis_backend import DiagnosisBackend, set_diagnosis_backend
from sysom_cli.memory.lib.classify_engine import run_classify
from sysom_cli.memory.lib.envelope_memory import recommended_specialty_cli_command
from sysom_cli.memory.memgraph.command import MemgraphHintCommand
from sysom_cli.memory.oom.command import OomHintCommand


_EMPTY_OOM_LOCAL: dict = {
    "hit_count": 0,
    "oom_event_count": 0,
    "oom_lines_total": None,
    "extraction_mode": "none",
    "oom_events_summary": [],
    "oom_digest": [],
    "time_range": None,
    "histogram_hour_local": [],
    "parsed_time_count": 0,
    "unparsed_wallclock_count": 0,
    "dmesg_relative_line_count": 0,
    "relative_boot_seconds_sample": [],
    "source_note_zh": "",
}


def _ok_invoke_payload() -> dict:
    return {
        "ok": True,
        "action": "diagnosis_invoke",
        "data": {
            "task_id": "task-xyz",
            "channel": "ecs",
            "region": "cn-test",
            "result": {"probe": 1},
        },
    }


class _FakeInvokeBackend(DiagnosisBackend):
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def invoke_specialty(self, service_name: str, ns: Namespace) -> dict:
        return self._payload


class MemoryDeepEnvelopeTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_diagnosis_backend(None)

    @patch("sysom_cli.lib.precheck_gate.remote_precheck_gate", return_value=(True, None))
    def test_memgraph_deep_local_envelope(self, _mock_gate: object) -> None:
        set_diagnosis_backend(_FakeInvokeBackend(_ok_invoke_payload()))
        ns = Namespace(
            deep_diagnosis=True,
            channel="ecs",
            timeout=300,
            verbose_envelope=False,
        )
        out = MemgraphHintCommand().execute_local(ns)
        self.assertTrue(out["ok"])
        self.assertEqual(out["execution"].get("phase"), "invoke_diagnosis")
        remote = out["data"]["remote"]
        self.assertTrue(remote["ok"])
        self.assertEqual(remote["service_name"], "memgraph")
        self.assertEqual(remote["task_id"], "task-xyz")
        self.assertEqual(out["agent"]["next"], [])
        self.assertIn("勿再重复", out["agent"]["summary"])

    @patch("sysom_cli.lib.precheck_gate.remote_precheck_gate", return_value=(True, None))
    def test_oom_deep_local_envelope(self, _mock_gate: object) -> None:
        set_diagnosis_backend(_FakeInvokeBackend(_ok_invoke_payload()))
        ns = Namespace(
            deep_diagnosis=True,
            channel="ecs",
            timeout=300,
            verbose_envelope=False,
        )
        out = OomHintCommand().execute_local(ns)
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["remote"]["service_name"], "oomcheck")
        self.assertEqual(out["agent"]["next"], [])

    def test_recommended_cli_appends_region_instance_when_both_set(self) -> None:
        ns = Namespace(region="cn-hangzhou", instance="i-abcd")
        cmd = recommended_specialty_cli_command("memgraph", ns)
        self.assertIn("--region cn-hangzhou", cmd)
        self.assertIn("--instance i-abcd", cmd)
        ns_partial = Namespace(region="cn-hangzhou", instance="")
        cmd2 = recommended_specialty_cli_command("oomcheck", ns_partial)
        self.assertNotIn("--region", cmd2)

    @patch("sysom_cli.memory.lib.classify_engine._top_rss_processes")
    @patch("sysom_cli.memory.lib.classify_engine.analyze_oom_local")
    @patch("sysom_cli.memory.lib.classify_engine._read_meminfo")
    def test_go_weak_hint_recommends_memgraph(
        self,
        mock_mem: object,
        mock_oom: object,
        mock_top: object,
    ) -> None:
        mock_mem.return_value = {
            "MemTotal": 16_000_000,
            "MemAvailable": 8_000_000,
            "SwapTotal": 1000,
            "SwapFree": 500,
        }
        mock_oom.return_value = dict(_EMPTY_OOM_LOCAL)
        mock_top.return_value = [("my___go_prog", "x", 1000)]
        r = run_classify()
        self.assertEqual(r.recommended_service_name, "memgraph")
        self.assertIn("go_workload", r.categories)


class FinalizeDiagnosisInvokeIdempotentTests(unittest.TestCase):
    """重复 finalize 不得把 data.remote.result 清空（历史上 io/net/load 曾二次包裹）。"""

    def test_double_finalize_preserves_remote_result(self) -> None:
        from sysom_cli.lib.invoke_envelope_finalize import finalize_diagnosis_invoke_envelope
        from sysom_cli.lib.schema import agent_block, envelope

        out = envelope(
            action="diagnosis_invoke",
            ok=True,
            agent=agent_block("normal", "x"),
            data={
                "task_id": "t1",
                "service_name": "iodiagnose",
                "channel": "ecs",
                "region": "cn-hangzhou",
                "result": {"payload": True},
            },
            execution={"subsystem": "invoke", "mode": "remote"},
        )
        ns = Namespace(verbose_envelope=False)
        once = finalize_diagnosis_invoke_envelope(out, ns, cli_subsystem="io")
        twice = finalize_diagnosis_invoke_envelope(copy.deepcopy(once), ns, cli_subsystem="io")
        self.assertEqual(once["data"]["remote"]["result"], {"payload": True})
        self.assertEqual(twice["data"]["remote"]["result"], {"payload": True})


class MergeDeepFromFinalizedInvokeTests(unittest.TestCase):
    """finalize_diagnosis_invoke_envelope 后 result 只在 data.remote，merge 须能读到。"""

    def test_merge_reads_result_from_nested_data_remote(self) -> None:
        from sysom_cli.lib.schema import agent_block, envelope
        from sysom_cli.memory.lib.memory_envelope_finalize import merge_deep_diagnosis_flat

        out = envelope(
            action="memory_memgraph_hint",
            ok=True,
            agent=agent_block("normal", "", findings=[], next_steps=[]),
            data={
                "recommended_service_name": "memgraph",
                "remote_analysis_value": {},
            },
            execution={"subsystem": "memory"},
        )
        inv = {
            "ok": True,
            "action": "diagnosis_invoke",
            "data": {
                "task_id": "t-finalized",
                "channel": "ecs",
                "region": "cn-hangzhou",
                "routing": {"recommended_service_name": "memgraph"},
                "remote": {
                    "ok": True,
                    "action": "diagnosis_invoke",
                    "service_name": "memgraph",
                    "task_id": "t-finalized",
                    "channel": "ecs",
                    "region": "cn-hangzhou",
                    "result": {"memgraph": "real_payload"},
                },
            },
        }
        merge_deep_diagnosis_flat(out, inv, service_name="memgraph")
        self.assertEqual(
            out["data"]["remote"]["result"],
            {"memgraph": "real_payload"},
        )


class OomDiagnosisHintsTests(unittest.TestCase):
    def test_extra_purpose_points_to_reference_and_params(self) -> None:
        from sysom_cli.memory.lib.envelope_memory import oom_diagnosis_invoke_extra_purpose_zh

        s = oom_diagnosis_invoke_extra_purpose_zh(0)
        self.assertIn("oomcheck.md", s)
        self.assertIn("--deep-diagnosis", s)

    def test_extra_purpose_multi_stays_short(self) -> None:
        from sysom_cli.memory.lib.envelope_memory import oom_diagnosis_invoke_extra_purpose_zh

        s = oom_diagnosis_invoke_extra_purpose_zh(3)
        self.assertIn("--oom-time", s)
        self.assertIn("3", s)
        self.assertLess(len(s), 600)


class RegistryNoGomemdumpTests(unittest.TestCase):
    def test_gomemdump_not_registered(self) -> None:
        from sysom_cli.core import registry as reg

        reg.CommandRegistry._discovered = False
        reg.CommandRegistry._commands.clear()
        reg.CommandRegistry._metadata.clear()
        reg.CommandRegistry._command_subsystem.clear()
        reg.CommandRegistry.discover_commands(top_level=True)
        reg.CommandRegistry.discover_commands()
        self.assertNotIn("gomemdump", reg.CommandRegistry.list_commands())
