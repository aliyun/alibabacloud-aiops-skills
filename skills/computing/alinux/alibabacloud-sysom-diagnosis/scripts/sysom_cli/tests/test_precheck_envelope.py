# -*- coding: utf-8 -*-
"""表驱动断言：precheck 信封形状与 remediation 关键词。"""
from __future__ import annotations

import unittest

from sysom_cli.lib.precheck_envelope import envelope_from_precheck_result


class PrecheckEnvelopeShapeTests(unittest.TestCase):
    def test_ok_success_light_guidance(self) -> None:
        env = envelope_from_precheck_result(
            {
                "ok": True,
                "method": "环境变量 AKSK",
                "message": "认证验证成功，拥有 SysOM 访问权限",
            }
        )
        self.assertTrue(env["ok"])
        g = env["data"]["guidance"]
        self.assertNotIn("guidance_mode", g)
        self.assertNotIn("session_rule", g)
        self.assertNotIn("guided_steps", g)

    def test_ecs_ram_role_compact_no_help(self) -> None:
        cr = {
            "ok": False,
            "error": "未找到有效的认证配置",
            "ecs_role_name": "ECSRamRoleForSysOM",
            "checked": [
                {"method": "ECS元数据", "status": "✓ 实例已绑定 RAM 角色: ECSRamRoleForSysOM"},
                {"method": "环境变量 AKSK", "status": "✗ 未配置"},
                {"method": "配置文件", "status": "✗ 未配置或配置无效"},
            ],
        }
        env = envelope_from_precheck_result(cr)
        self.assertFalse(env["ok"])
        d = env["data"]
        self.assertEqual(d["path_summary"]["primary_path"], "ecs_ram_role")
        self.assertNotIn("service_activated", d)
        self.assertNotIn("help", d)
        self.assertIn("progress", d["path_summary"])
        self.assertTrue(d["path_summary"]["progress"]["metadata_role_bound"])
        self.assertNotIn("help", d)
        self.assertNotIn("suggestion", d)
        self.assertNotIn("guidance_mode", d["guidance"])
        self.assertEqual(len(env["agent"]["findings"]), 2)
        rem = "\n".join(d["remediation"])
        self.assertIn("ECS RAM Role", rem)
        self.assertNotIn("curl", rem.lower())

    def test_access_key_path_env_only_remediation(self) -> None:
        cr = {
            "ok": False,
            "error": "权限不足",
            "error_code": "insufficient_permissions",
            "checked": [
                {"method": "ECS元数据", "status": "✗ 未检测到"},
                {
                    "method": "环境变量 AKSK",
                    "status": "✗ 权限不足，需要 AliyunSysomFullAccess 权限",
                },
                {"method": "配置文件", "status": "✗ 未配置或配置无效"},
            ],
        }
        env = envelope_from_precheck_result(cr)
        self.assertEqual(env["data"]["path_summary"]["primary_path"], "access_key")
        self.assertNotIn(
            "service_activated", env["data"],
            "权限不足时未调用成功 InitialSysom，不应输出 service_activated",
        )
        rem = env["data"]["remediation"]
        joined = "\n".join(rem)
        self.assertIn("环境变量", joined)
        self.assertIn("主路径：RAM 用户 AccessKey", joined)

    def test_configure_identity_has_help(self) -> None:
        cr = {
            "ok": False,
            "error": "未找到有效的认证配置",
            "checked": [
                {"method": "ECS元数据", "status": "✗ 未检测到"},
                {"method": "环境变量 AKSK", "status": "✗ 未配置"},
                {"method": "配置文件", "status": "✗ 未配置或配置无效"},
            ],
            "help": {"aksk": "x", "ram_role": "y", "permission": "z"},
        }
        env = envelope_from_precheck_result(cr)
        self.assertEqual(env["data"]["path_summary"]["primary_path"], "configure_identity")
        self.assertNotIn("service_activated", env["data"])
        self.assertNotIn("help", env["data"])
        self.assertIn("auth_path_choice", env["data"]["guidance"])

    def test_activation_two_findings(self) -> None:
        cr = {
            "ok": False,
            "error": "服务未开通",
            "error_code": "service_not_activated",
            "checked": [
                {"method": "ECS元数据", "status": "✗ 未检测到"},
                {"method": "环境变量 AKSK", "status": "✗ 未配置"},
                {"method": "配置文件 AKSK", "status": "✗ 服务未开通"},
            ],
            "suggestion": "开通",
            "help": {},
        }
        env = envelope_from_precheck_result(cr)
        self.assertEqual(len(env["agent"]["findings"]), 2)
        self.assertIn("处理说明", env["agent"]["findings"][1]["title"])
        self.assertIs(
            env["data"].get("service_activated"),
            False,
            "InitialSysom 已明确返回未开通/角色未就绪时应为 false",
        )


if __name__ == "__main__":
    unittest.main()
