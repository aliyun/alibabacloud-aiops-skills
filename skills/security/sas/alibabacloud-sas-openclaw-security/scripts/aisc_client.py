"""阿里云 AISC OpenAPI 客户端。"""

from __future__ import annotations

from .base_client import BaseClient


class AiscClient(BaseClient):
    """AISC OpenAPI 客户端（aliyun CLI 实现）。"""

    PRODUCT_NAME = "AISC"

    def __init__(self):
        super().__init__("cn-shanghai")

    def get_ai_agent_plugin_command(self) -> dict:
        """调用 GetAIAgentPluginKey，获取 OpenClaw 安全助手的安装命令。

        注意：底层 API 名称为 GetAIAgentPluginKey，响应字段为 InstallKey，
        但其实际含义是一条完整的 shell 安装命令（install command），
        而非传统意义上的密钥（key/token）。方法名使用 command 以准确描述语义。

        CLI 等价命令：
            aliyun aisc GetAIAgentPluginKey
                --version 2026-01-01
                --endpoint aisc.cn-shanghai.aliyuncs.com
                --force
        """
        # API Action 名称保持原样：GetAIAgentPluginKey（不可改动）
        args = [
            "aisc",
            "GetAIAgentPluginKey",  # API 名称，勿改
            "--version",
            "2026-01-01",
            "--endpoint",
            "aisc.cn-shanghai.aliyuncs.com",
            "--force",
        ]
        return self._run_cli(args)
