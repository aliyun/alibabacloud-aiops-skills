# -*- coding: utf-8 -*-
"""Mock 成功响应时，各 SysOM 专项信封须含非空的 data.remote.result（防二次 finalize 等回归）。"""
from __future__ import annotations

import unittest
from argparse import Namespace
from typing import List

from sysom_cli.core import registry as reg
from sysom_cli.diagnosis.invoke.command import DiagnosisInvokeCommand
from sysom_cli.lib.diagnosis_backend import namespace_for_diagnosis_invoke
from sysom_cli.lib.diagnosis_helper import DiagnoseResultCode, DiagnosisRequest, DiagnosisResponse


def _ensure_registry() -> None:
    reg.CommandRegistry._discovered = False
    reg.CommandRegistry._commands.clear()
    reg.CommandRegistry._metadata.clear()
    reg.CommandRegistry._command_subsystem.clear()
    reg.CommandRegistry.discover_commands(top_level=True)
    reg.CommandRegistry.discover_commands()


def _specialty_ns() -> Namespace:
    return Namespace(
        channel="ecs",
        region="cn-hangzhou",
        instance="i-mockprobe",
        params=None,
        params_file=None,
        timeout=30,
        poll_interval=1,
        verbose_envelope=False,
    )


async def _fake_diagnosis_execute(self: object, req: DiagnosisRequest) -> DiagnosisResponse:
    return DiagnosisResponse(
        code=DiagnoseResultCode.SUCCESS,
        message="",
        task_id="mock-task-id",
        result={"mock_ok": True, "service_name": req.service_name},
    )


class AllRemoteDiagnosisEnvelopeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_registry()

    # io / net / load 已裁剪，仅保留内存诊断专项
    SPECIALTY_CLI_NAMES: List[str] = []
    # memory 深度诊断复用同一 invoke 后端的 service_name
    MEMORY_INVOKE_SERVICE_NAMES: List[str] = ["memgraph", "oomcheck", "javamem"]

    def test_specialty_commands_remote_result_populated_under_mock(self) -> None:
        from unittest.mock import patch

        with patch(
            "sysom_cli.diagnosis.invoke.command.DiagnosisMCPHelper.execute",
            new=_fake_diagnosis_execute,
        ):
            for name in self.SPECIALTY_CLI_NAMES:
                with self.subTest(command=name):
                    cmd = reg.CommandRegistry.get(name)
                    out = cmd.execute_remote(_specialty_ns())
                    self.assertTrue(out.get("ok"), msg=f"{name}: {out}")
                    remote = (out.get("data") or {}).get("remote") or {}
                    self.assertIsInstance(remote, dict)
                    res = remote.get("result")
                    self.assertIsNotNone(
                        res,
                        msg=f"{name}: data.remote.result 不应为 null，实际 remote keys={list(remote)}",
                    )
                    self.assertIsInstance(res, dict)
                    self.assertEqual(res.get("service_name"), name)

    def test_invoke_command_all_service_names_remote_result(self) -> None:
        from unittest.mock import patch

        all_services = self.SPECIALTY_CLI_NAMES + self.MEMORY_INVOKE_SERVICE_NAMES
        with patch(
            "sysom_cli.diagnosis.invoke.command.DiagnosisMCPHelper.execute",
            new=_fake_diagnosis_execute,
        ):
            for svc in all_services:
                with self.subTest(service_name=svc):
                    ns = namespace_for_diagnosis_invoke(svc, _specialty_ns())
                    out = DiagnosisInvokeCommand().execute_remote(ns)
                    self.assertTrue(out.get("ok"), msg=f"{svc}: {out}")
                    remote = (out.get("data") or {}).get("remote") or {}
                    res = remote.get("result")
                    self.assertIsNotNone(res, msg=f"{svc}: data.remote.result 缺失")
                    self.assertIsInstance(res, dict)
                    self.assertEqual(res.get("service_name"), svc)
                    sub = reg.CommandRegistry.get_subsystem(svc)
                    if sub:
                        self.assertEqual((out.get("execution") or {}).get("subsystem"), sub)


if __name__ == "__main__":
    unittest.main()
