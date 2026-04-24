"""阿里云 SAS（云安全中心）OpenAPI 客户端。

封装 OpenClaw 安全运营所需的核心 API：
  - DescribePropertyScaDetail  查询 SCA 组件实例
  - DescribeVulList            查询漏洞列表
  - ModifyPushAllTask          下发漏洞/基线检查任务
  - DescribeCheckWarningSummary 查询基线汇总（可按 UUID 过滤）
  - DescribeCheckWarnings      按 UUID + RiskId 查询详情
  - DescribeSuspEvents         查询告警事件
  - GetAssetDetailByUuid       按 UUID 查询资产详情
"""

from __future__ import annotations

from .base_client import BaseClient


class SasClient(BaseClient):
    """SAS OpenAPI 客户端（aliyun CLI 实现）。"""

    PRODUCT_NAME = "云安全中心"

    def __init__(self, region: str | None = None):
        super().__init__(region or "cn-shanghai")

    # ---------------------------------------------------------------
    # 1. 查询 SCA 组件实例（OpenClaw）
    # ---------------------------------------------------------------

    def describe_property_sca_detail(
        self,
        biz: str | None = None,
        sca_name_pattern: str | None = None,
        name: str | None = None,
        max_pages: int | None = None,
        page_size: int | None = None,
    ) -> list[dict]:
        """查询 SCA 软件组件详情列表。

        Args:
            biz: 业务类型，如 'sca_ai' 表示 AI 组件
            sca_name_pattern: 组件名称模糊匹配
            name: 主机名称/IP 模糊过滤（对应 --Remark）
            max_pages: 最大翻页数
            page_size: 每页条数

        CLI 等价命令：
            aliyun sas describe-property-sca-detail --lang zh
                [--biz <biz>] [--sca-name-pattern <pattern>] [--remark <name>]
                --page-size <n> --current-page <p>
        """
        args = ["sas", "describe-property-sca-detail", "--lang", "zh"]
        if biz:
            args += ["--biz", biz]
        if sca_name_pattern:
            args += ["--sca-name-pattern", sca_name_pattern]
        if name:
            args += ["--remark", name]
        return self._paginate_cli(args, "Propertys", max_pages, page_size)

    # ---------------------------------------------------------------
    # 2. 查询漏洞列表
    # ---------------------------------------------------------------

    def describe_vul_list(
        self,
        vul_type: str = "cve",
        dealed: str = "n",
        name: str | None = None,
        necessity: str | None = None,
        uuids: str | None = None,
        max_pages: int | None = None,
        page_size: int | None = None,
    ) -> list[dict]:
        """查询漏洞列表。

        Args:
            vul_type: 漏洞类型 cve/sys/cms/emg 等
            dealed: 是否已处理 y/n
            name: 漏洞名称（精确匹配）
            necessity: 修复紧急度
            uuids: 指定主机 UUID（逗号分隔）
            max_pages: 最大翻页数
            page_size: 每页条数

        CLI 等价命令：
            aliyun sas describe-vul-list --lang zh --type <type> --dealed <y/n>
                [--name <name>] [--necessity <level>] [--uuids <uuids>]
                --page-size <n> --current-page <p>
        """
        args = [
            "sas",
            "describe-vul-list",
            "--lang",
            "zh",
            "--type",
            vul_type,
            "--dealed",
            dealed,
        ]
        if name:
            args += ["--name", name]
        if necessity:
            args += ["--necessity", necessity]
        if uuids:
            args += ["--uuids", uuids]
        return self._paginate_cli(args, "VulRecords", max_pages, page_size)

    # ---------------------------------------------------------------
    # 3. 下发漏洞/基线检查任务
    # ---------------------------------------------------------------

    def modify_push_all_task(
        self,
        uuids: str,
        tasks: str = "OVAL_ENTITY,CMS,SYSVUL,SCA,HEALTH_CHECK",
    ) -> dict:
        """根据 UUID 下发漏洞和基线检查任务。

        CLI 等价命令：
            aliyun sas modify-push-all-task --uuids <uuids> --tasks <tasks>
        """
        args = [
            "sas",
            "modify-push-all-task",
            "--uuids",
            uuids,
            "--tasks",
            tasks,
        ]
        return self._run_cli(args)

    # ---------------------------------------------------------------
    # 4. 基线检查（按 UUID）
    # ---------------------------------------------------------------

    def describe_check_warning_summary(
        self,
        uuids: str | None = None,
    ) -> dict:
        """查询基线检查汇总结果。

        Args:
            uuids: 资产 UUID（逗号分隔），不传则返回全部资产汇总

        CLI 等价命令：
            aliyun sas describe-check-warning-summary [--uuids <uuids>]
        """
        args = ["sas", "describe-check-warning-summary"]
        if uuids:
            args += ["--uuids", uuids]
        return self._run_cli(args)

    def describe_check_warnings(
        self,
        uuid: str,
        risk_id: int,
    ) -> dict:
        """根据 UUID + 风险项 ID 查询基线检查详情。

        CLI 等价命令：
            aliyun sas describe-check-warnings --lang zh
                --uuid <uuid> --risk-id <risk_id>
                --page-size 100 --current-page 1
        """
        args = [
            "sas",
            "describe-check-warnings",
            "--lang",
            "zh",
            "--uuid",
            uuid,
            "--risk-id",
            str(risk_id),
            "--page-size",
            "100",
            "--current-page",
            "1",
        ]
        return self._run_cli(args)

    # ---------------------------------------------------------------
    # 5. 按 UUID 查询资产详情
    # ---------------------------------------------------------------

    def get_asset_detail_by_uuid(self, uuid: str) -> dict:
        """查询云安全中心单个资产的详细信息。

        Args:
            uuid: 资产 UUID（可通过 describe_property_sca_detail 获取）

        Returns:
            AssetDetail 字典，包含主机名、IP、OS、CPU/内存、磁盘、
            客户端状态、区域等字段。

        CLI 等价命令：
            aliyun sas get-asset-detail-by-uuid --lang zh --uuid <uuid>
        """
        args = [
            "sas", "get-asset-detail-by-uuid",
            "--lang", "zh",
            "--uuid", uuid,
        ]
        body = self._run_cli(args)
        return body.get("AssetDetail", body)

    def describe_susp_events(
        self,
        dealed: str = "N",
        levels: str | None = None,
        uuids: str | None = None,
        name: str | None = None,
        max_pages: int | None = None,
        page_size: int | None = None,
    ) -> list[dict]:
        """查询告警事件列表。

        Args:
            dealed: 是否已处理 Y/N
            levels: 告警级别过滤（serious/suspicious/remind，逗号分隔）
            uuids: 指定主机 UUID（逗号分隔）
            name: 受影响资产名称过滤
            max_pages: 最大翻页数
            page_size: 每页条数

        CLI 等价命令：
            aliyun sas describe-susp-events --lang zh --dealed <Y/N>
                [--levels <levels>] [--uuids <uuids>] [--name <name>]
                --page-size <n> --current-page <p>
        """
        args = [
            "sas",
            "describe-susp-events",
            "--lang",
            "zh",
            "--dealed",
            dealed,
        ]
        if levels:
            args += ["--levels", levels]
        if uuids:
            args += ["--uuids", uuids]
        if name:
            args += ["--name", name]
        return self._paginate_cli(args, "SuspEvents", max_pages, page_size)
