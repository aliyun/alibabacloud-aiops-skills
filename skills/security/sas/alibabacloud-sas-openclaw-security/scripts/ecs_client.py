"""阿里云 ECS（云服务器）OpenAPI 客户端。

全部通过 aliyun CLI 实现，无需 SDK 依赖。
"""

from __future__ import annotations
import base64
import time

from .base_client import APIError, BaseClient


class EcsClient(BaseClient):
    """ECS OpenAPI 客户端（aliyun CLI 实现）。"""

    PRODUCT_NAME = "云服务器 ECS"
    POLL_RETRY_TIMES = 3
    POLL_RETRY_DELAY = 2

    def __init__(self, region: str | None = None):
        super().__init__(region or "cn-hangzhou")

    def run_command(
        self,
        instance_ids: list[str],
        command_content: str,
        command_type: str = "RunShellScript",
        region: str | None = None,
        name: str | None = None,
        description: str | None = None,
        timeout: int | None = None,
        working_dir: str | None = None,
        username: str | None = None,
        keep_command: bool | None = None,
    ) -> dict:
        """通过云助手在 ECS 实例上执行命令。

        Args:
            instance_ids: ECS 实例 ID 列表
            command_content: 命令内容（明文，自动进行 Base64 编码）
            command_type: 命令类型（默认 RunShellScript）
            region: 区域 ID，未传时使用客户端默认区域
            name: 命令名称
            description: 命令描述
            timeout: 超时时间（秒）
            working_dir: 执行目录
            username: 执行用户
            keep_command: 是否保留命令

        CLI 等价命令：
            aliyun ecs run-command --biz-region-id <region>
                --type RunShellScript --command-content <b64> --content-encoding Base64
                --instance-id <id1> [<id2> ...]
                [--name <name>] [--timeout <sec>] ...
        """
        if not instance_ids:
            raise ValueError("instance_ids 不能为空")

        effective_region = region or self._region
        command_b64 = base64.b64encode(command_content.encode()).decode()
        args = [
            "ecs",
            "run-command",
            "--biz-region-id",
            effective_region,
            "--type",
            command_type,
            "--command-content",
            command_b64,
            "--content-encoding",
            "Base64",
        ]
        args += ["--instance-id"] + instance_ids
        if name:
            args += ["--name", name]
        if description:
            args += ["--description", description]
        if timeout is not None:
            args += ["--timeout", str(timeout)]
        if working_dir:
            args += ["--working-dir", working_dir]
        if username:
            args += ["--username", username]
        if keep_command is not None:
            args += ["--keep-command", str(keep_command).lower()]

        return self._run_cli(args, region=effective_region)

    def get_command_result_by_invoke_id(
        self,
        invoke_id: str,
        instance_id: str,
    ) -> dict:
        """按 invoke_id 查询单台实例的命令执行结果。

        CLI 等价命令：
            aliyun ecs describe-invocation-results --biz-region-id <region>
                --invoke-id <invoke_id> --instance-id <instance_id>
        """
        args = [
            "ecs",
            "describe-invocation-results",
            "--biz-region-id",
            self._region,
            "--invoke-id",
            invoke_id,
            "--instance-id",
            instance_id,
        ]
        body = self._run_cli(args)

        invocation = body.get("Invocation", {})
        results = invocation.get("InvocationResults", {})
        result_list = results.get("InvocationResult", [])
        if not result_list:
            raise APIError(
                "DescribeInvocationResults",
                f"未找到执行结果: invoke_id={invoke_id}, " f"instance_id={instance_id}",
            )
        item = result_list[0]
        if not isinstance(item, dict):
            raise APIError(
                "DescribeInvocationResults",
                "执行结果格式异常",
            )
        return item

    @staticmethod
    def _is_retryable_poll_error(err: Exception) -> bool:
        """判断轮询结果查询是否命中了可重试的瞬时错误。"""
        msg = str(err).lower()
        return any(
            keyword in msg
            for keyword in [
                "connection aborted",
                "remotedisconnected",
                "remote end closed connection without response",
                "read timed out",
                "connect timeout",
                "connection reset by peer",
                "temporarily unavailable",
                "service unavailable",
                "502 bad gateway",
                "503 service unavailable",
                "504 gateway timeout",
            ]
        )

    def get_command_result_with_retry(
        self,
        invoke_id: str,
        instance_id: str,
        retries: int | None = None,
        retry_delay: int | None = None,
    ) -> dict:
        """查询执行结果，并对瞬时网络错误做短暂重试。"""
        max_retries = self.POLL_RETRY_TIMES if retries is None else retries
        base_delay = self.POLL_RETRY_DELAY if retry_delay is None else retry_delay

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return self.get_command_result_by_invoke_id(
                    invoke_id=invoke_id,
                    instance_id=instance_id,
                )
            except Exception as err:
                last_error = err
                if attempt >= max_retries or not self._is_retryable_poll_error(err):
                    raise
                time.sleep(base_delay * (attempt + 1))

        raise APIError(
            "DescribeInvocationResults",
            f"查询执行结果失败: {last_error}",
        )

    def wait_command_result(
        self,
        invoke_id: str,
        instance_id: str,
        timeout: int = 60,
        max_polls: int = 10,
        allow_nonzero_exit: bool = False,
    ) -> dict:
        """循环等待命令执行结果并返回最终状态。"""
        if max_polls <= 0:
            raise ValueError("max_polls 必须大于 0")
        if timeout <= 0:
            raise ValueError("timeout 必须大于 0")

        sleep_interval = max(timeout / max_polls, 1)
        pending_status = {"Pending", "Running", "Stopping"}

        last_result: dict | None = None
        for _ in range(max_polls):
            time.sleep(sleep_interval)
            result = self.get_command_result_with_retry(
                invoke_id=invoke_id,
                instance_id=instance_id,
            )
            last_result = result
            status = result.get("InvocationStatus", "")
            if status in pending_status:
                continue

            output_b64 = result.get("Output", "")
            output = self._decode_output(output_b64)
            final_result = {
                "InvocationStatus": status,
                "ExitCode": result.get("ExitCode"),
                "Output": output,
                "RawOutput": output_b64,
                "ErrorCode": result.get("ErrorCode"),
                "ErrorInfo": result.get("ErrorInfo"),
                "Result": result,
            }

            if status == "Success" or allow_nonzero_exit:
                return final_result

            raise APIError(
                "DescribeInvocationResults",
                f"命令执行失败: status={status}, "
                f"exit_code={result.get('ExitCode')}, "
                f"error_code={result.get('ErrorCode')}, "
                f"error_info={result.get('ErrorInfo')}, "
                f"output={repr(output)}",
            )

        raise TimeoutError(
            f"获取命令执行结果超时: timeout={timeout}s, "
            f"invoke_id={invoke_id}, last_result={last_result}"
        )

    @staticmethod
    def _decode_output(output_b64: str) -> str:
        """解码 Base64 输出，失败时返回原文。"""
        if not output_b64:
            return ""
        try:
            return base64.b64decode(output_b64).decode("utf-8", errors="replace")
        except Exception:
            return output_b64
