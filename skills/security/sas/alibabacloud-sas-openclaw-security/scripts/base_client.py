"""阿里云 OpenAPI 客户端基类。"""

from __future__ import annotations

import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 异常类
# ---------------------------------------------------------------------------


class CredentialError(Exception):
    """aliyun CLI 未安装或未配置凭据"""


class ProductNotEnabledError(Exception):
    """云产品未开通"""


class APIError(Exception):
    """API 调用失败"""

    def __init__(self, api_name: str, message: str):
        self.api_name = api_name
        super().__init__(f"{api_name}: {message}")


# ---------------------------------------------------------------------------
# 基础客户端
# ---------------------------------------------------------------------------


class BaseClient:
    """阿里云 OpenAPI 客户端基类（aliyun CLI 实现）。"""

    DEFAULT_PAGE_SIZE = 20
    DEFAULT_MAX_PAGES = 3
    MAX_RECORDS = 200

    PRODUCT_NAME: str = ""

    def __init__(self, region: str | None = None):
        self._region = region or os.environ.get("ALICLOUD_REGION_ID", "cn-shanghai")

    def _is_not_enabled_error(self, e: Exception) -> bool:
        """判断是否为产品未开通错误。"""
        msg = str(e).lower()
        return any(
            kw in msg
            for kw in [
                "notopened",
                "not_opened",
                "forbidden",
                "nosubscription",
                "not activated",
                "未开通",
            ]
        )

    def _run_cli(
        self,
        args: list[str],
        region: str | None = None,
    ) -> dict:
        """执行 aliyun CLI 命令并返回解析后的 JSON。

        Args:
            args: 产品 + API + 参数，如 ["sas", "DescribeVulList", "--Type", "cve"]
            region: 覆盖 self._region 的区域，不传则使用 self._region
        """
        effective_region = region or self._region
        cmd = [
            "aliyun",
            "--region", effective_region,
            "--user-agent", "AlibabaCloud-Agent-Skills",
        ] + args
        api_name = args[1] if len(args) > 1 else args[0]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise APIError(api_name, "CLI 命令超时（30s）")
        except FileNotFoundError:
            raise CredentialError(
                "未找到 aliyun CLI，请先安装：https://help.aliyun.com/zh/cli/installation"
            )

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or proc.stdout.strip()
            if self._is_not_enabled_error(Exception(err_msg)):
                raise ProductNotEnabledError(
                    f"{self.PRODUCT_NAME}未开通或当前版本不支持 {api_name}。"
                    f"\n原始错误: {err_msg}"
                )
            raise APIError(api_name, err_msg)

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise APIError(
                api_name,
                f"JSON 解析失败: {exc}\n输出: {proc.stdout[:300]}",
            )

    def _paginate_cli(
        self,
        base_args: list[str],
        items_key: str,
        max_pages: int | None = None,
        page_size: int | None = None,
        region: str | None = None,
    ) -> list[dict]:
        """通用 CLI 分页，自动翻页。

        Args:
            base_args: 不含 --PageSize/--CurrentPage 的 CLI 参数列表
            items_key: 响应 JSON 中条目列表的键名
            max_pages: 最大翻页数
            page_size: 每页条数
            region: 覆盖 self._region 的区域
        """
        ps = page_size or self.DEFAULT_PAGE_SIZE
        mp = max_pages or self.DEFAULT_MAX_PAGES
        all_items: list[dict] = []
        for page in range(1, mp + 1):
            args = base_args + [
                "--PageSize",
                str(ps),
                "--CurrentPage",
                str(page),
            ]
            body = self._run_cli(args, region=region)
            items = body.get(items_key, [])
            all_items.extend(items)
            total = body.get("TotalCount") or body.get("PageInfo", {}).get(
                "TotalCount", 0
            )
            if len(all_items) >= total or len(items) < ps:
                break
            if len(all_items) >= self.MAX_RECORDS:
                logger.warning(
                    "已达到 %d 条记录上限，停止分页",
                    self.MAX_RECORDS,
                )
                break
        return all_items
