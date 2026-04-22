#!/usr/bin/env python3
"""baseline.py — 云安全中心基线/系统基线批量导出工具

用法:
  # 导出所有启用账号的云平台配置检查结果
  uv run baseline.py export-cspm

  # 仅导出指定账号
  uv run baseline.py export-cspm --account-id 1234567890

  # 导出系统基线风险列表
  uv run baseline.py export-system-warning
  uv run baseline.py export-system-warning --account-id 1234567890
"""

import argparse
import asyncio
import json
import shutil
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

# 将 scripts 目录加入路径以便导入同级模块
sys.path.insert(0, str(Path(__file__).parent))
from accounts import get_caller_account_id, get_enabled_accounts  # noqa: E402
from merge import merge_excel  # noqa: E402

TODAY = date.today().strftime("%Y%m%d")
QPS_LIMIT = 5  # API 并发上限
ALIYUN_USER_AGENT_HEADER = "User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-sas-multiaccount-manage"
CLI_CONNECT_TIMEOUT_SECONDS = 10
CLI_READ_TIMEOUT_SECONDS = 60
DOWNLOAD_TIMEOUT_SECONDS = 60

# 全局信号量，在事件循环内初始化

# 当前凭证的主账号 ID，在 do_export() 中初始化
_caller_account_id = ""

# SAS API 地域，在 do_export() 中初始化
_region_id = "cn-shanghai"

# 可跳过的 API 错误码（账号无权限/免费版限制等），静默忽略
_SKIP_ERROR_CODES = {"FreeVersionNotPermit", "NoPermission", "Forbidden"}


class AccountSkippedError(Exception):
    """账号因权限不足等原因被跳过，不中断整体流程。"""
    def __init__(self, account_id, reason):
        self.account_id = account_id
        self.reason = reason
        super().__init__(f"账号 {account_id} 跳过: {reason}")

# ────────────────────────────── 异步 API 封装 ──────────────────────────────


async def _run_aliyun_async(args, account_id=""):
    """异步运行 aliyun CLI，通过信号量将并发 API 调用限制在 QPS ≤ 5。

    对可跳过的错误码（如 FreeVersionNotPermit）抛出 AccountSkippedError。
    """
    async with _api_sem:
        proc = await asyncio.create_subprocess_exec(
            "aliyun",
            "--header",
            ALIYUN_USER_AGENT_HEADER,
            "--connect-timeout",
            str(CLI_CONNECT_TIMEOUT_SECONDS),
            "--read-timeout",
            str(CLI_READ_TIMEOUT_SECONDS),
            "sas",
            "--region",
            _region_id,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

    err_text = stderr.decode()
    if proc.returncode != 0:
        # 检查是否属于可跳过的错误码（静默忽略）
        for code in _SKIP_ERROR_CODES:
            if code in err_text:
                raise AccountSkippedError(account_id, code)
        print(f"aliyun CLI 调用失败:\n{err_text}", file=sys.stderr)
        raise RuntimeError("aliyun CLI error")
    # returncode==0 但 stderr 中仍含可跳过错误码时也忽略
    for code in _SKIP_ERROR_CODES:
        if code in err_text:
            raise AccountSkippedError(account_id, code)
    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError:
        print(f"响应解析失败:\n{stdout.decode()}", file=sys.stderr)
        raise


async def start_export_async(export_type, account_id, params=None):
    """发起导出任务，返回 export_id。"""
    cli_args = [
        "export-record",
        "--lang", "zh",
        "--export-type", export_type,
    ]
    if account_id != _caller_account_id:
        cli_args += ["--resource-directory-account-id", str(account_id)]
    if params:
        cli_args += ["--params", params]

    data = await _run_aliyun_async(cli_args, account_id)
    export_id = str(data["Id"])
    print(f"  [提交] 账号 {account_id}，export_id={data['Id']}")
    return export_id


async def wait_for_export_async(export_id, account_id, poll_interval=5):
    """轮询导出状态，成功后返回下载链接。"""
    while True:
        cli_args = [
            "describe-export-info",
            "--export-id", export_id,
        ]
        if account_id != _caller_account_id:
            cli_args += ["--resource-directory-account-id", str(account_id)]
        data = await _run_aliyun_async(cli_args, account_id)
        status = data.get("ExportStatus", "")

        if status == "success":
            return data["Link"]
        if status in ("failed", "error"):
            raise RuntimeError(f"账号 {account_id} 导出失败，状态={status}")
        await asyncio.sleep(poll_interval)


async def download_and_extract_async(link, account_id, prefix):
    """异步下载 zip，解压，重命名为 {prefix}-{account_id}-{date}.xlsx。"""
    zip_path = Path(f"{prefix}-{account_id}-{TODAY}.zip")
    print(f"  [下载] 账号 {account_id}...")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _download_with_timeout, link, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        zf.extractall(path=zip_path.parent)
        extracted = zip_path.parent / names[0]

    output_path = Path(f"{prefix}-{account_id}-{TODAY}.xlsx")
    if extracted != output_path:
        extracted.rename(output_path)
    if zip_path.exists():
        zip_path.unlink()

    return str(output_path)


def _download_with_timeout(link, output_path):
    """下载文件并设置超时，避免网络异常时无限阻塞。"""
    with urllib.request.urlopen(link, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        with Path(output_path).open("wb") as fp:
            shutil.copyfileobj(response, fp)


async def _wait_and_download(export_id, account_id, prefix):
    """等待导出完成后下载，返回 merge 所需的 input dict。"""
    link = await wait_for_export_async(export_id, account_id)
    xlsx_path = await download_and_extract_async(link, account_id, prefix)
    return {"filename": xlsx_path, "account_id": account_id}


# ────────────────────────────── 异步导出流程 ──────────────────────────────


async def do_export_async(export_type, prefix, merged_name, account_ids, params=None):
    """并发导出流程：

    阶段 1 — 并发提交所有账号的导出任务（QPS ≤ 5）
    阶段 2 — 并发轮询 + 下载解压（QPS ≤ 5）
    阶段 3 — 合并所有 xlsx
    """
    global _api_sem
    _api_sem = asyncio.Semaphore(QPS_LIMIT)

    if not account_ids:
        print("错误: 没有可用账号", file=sys.stderr)
        sys.exit(1)

    print(f"共 {len(account_ids)} 个账号待导出（耗时操作，请耐心等待）")

    # 阶段 1：并发提交所有导出任务
    submit_results = await asyncio.gather(
        *[start_export_async(export_type, aid, params) for aid in account_ids],
        return_exceptions=True,
    )

    pending = []  # (export_id, account_id)
    skipped = []
    for aid, res in zip(account_ids, submit_results):
        if isinstance(res, AccountSkippedError):
            skipped.append(aid)
        elif isinstance(res, BaseException):
            print(f"  [失败] 账号 {aid}: {res}", file=sys.stderr)
        else:
            pending.append((res, aid))

    if not pending:
        print(f"所有账号均被跳过（{len(skipped)} 个），无可合并数据")
        return

    # 阶段 2：并发等待 + 下载解压
    download_results = await asyncio.gather(
        *[_wait_and_download(eid, aid, prefix) for eid, aid in pending],
        return_exceptions=True,
    )

    inputs = []
    failed = []
    for (_, aid), res in zip(pending, download_results):
        if isinstance(res, AccountSkippedError):
            skipped.append(aid)
        elif isinstance(res, BaseException):
            print(f"  [失败] 账号 {aid}: {res}", file=sys.stderr)
            failed.append(aid)
        else:
            print(f"  [成功] 账号 {aid}")
            inputs.append(res)

    if skipped:
        print(f"跳过 {len(skipped)} 个账号: {', '.join(skipped)}")
    if failed:
        print(f"失败 {len(failed)} 个账号: {', '.join(failed)}", file=sys.stderr)

    if not inputs:
        print("没有成功下载的文件，跳过合并")
        return

    # 阶段 3：合并
    merge_excel(merged_name, inputs)

    # 阶段 4：删除临时 xlsx 文件
    for item in inputs:
        tmp = Path(item["filename"])
        if tmp.exists():
            tmp.unlink()
    print(f"已生成: {merged_name}（共 {len(inputs)} 个账号，已清理临时文件）")


def do_export(export_type, prefix, merged_name, account_ids, params=None, region_id="cn-shanghai"):
    """同步入口，内部通过 asyncio.run 驱动异步流程。"""
    global _caller_account_id, _region_id
    _caller_account_id = get_caller_account_id()
    _region_id = region_id
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        do_export_async(export_type, prefix, merged_name, account_ids, params)
    )


# ────────────────────────────── CLI 子命令 ──────────────────────────────


def cmd_export_cspm(args):
    """导出云平台配置检查结果（baselineCspm）。"""
    if args.account_id:
        account_ids = [args.account_id]
    else:
        accounts = get_enabled_accounts()
        account_ids = [a["AccountId"] for a in accounts]

    do_export(
        export_type="baselineCspm",
        prefix="baseline-cspm",
        merged_name=f"baseline-cspm-merged-{TODAY}.xlsx",
        account_ids=account_ids,
        region_id=args.region_id,
    )


def cmd_export_system_warning(args):
    """导出系统基线风险列表（exportHcWarning）。"""
    if args.account_id:
        account_ids = [args.account_id]
    else:
        accounts = get_enabled_accounts()
        account_ids = [a["AccountId"] for a in accounts]

    params = json.dumps(
        {
            "CheckLevel": "high,medium,low",
            "CheckWarningStatusList": [1, 3, 6, 8],
            "Source": "default",
        },
        ensure_ascii=False,
    )

    do_export(
        export_type="exportHcWarning",
        prefix="system-warning",
        merged_name=f"system-warning-merged-{TODAY}.xlsx",
        account_ids=account_ids,
        params=params,
        region_id=args.region_id,
    )


# ────────────────────────────── 入口 ──────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="云安全中心基线批量导出工具")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # export-cspm
    p_cspm = sub.add_parser(
        "export-cspm",
        help="导出云平台配置检查结果（baselineCspm）",
    )
    p_cspm.add_argument(
        "--account-id",
        metavar="ACCOUNT_ID",
        help="指定单个账号 ID（默认导出所有启用账号）",
    )
    p_cspm.add_argument(
        "--region-id",
        dest="region_id",
        choices=["cn-shanghai", "ap-southeast-1"],
        default="cn-shanghai",
        help="SAS API 地域：cn-shanghai（中国大陆，默认）/ ap-southeast-1（非中国大陆）",
    )

    # export-system-warning
    p_warn = sub.add_parser(
        "export-system-warning",
        help="导出系统基线风险列表（exportHcWarning）",
    )
    p_warn.add_argument(
        "--account-id",
        metavar="ACCOUNT_ID",
        help="指定单个账号 ID（默认导出所有启用账号）",
    )
    p_warn.add_argument(
        "--region-id",
        dest="region_id",
        choices=["cn-shanghai", "ap-southeast-1"],
        default="cn-shanghai",
        help="SAS API 地域：cn-shanghai（中国大陆，默认）/ ap-southeast-1（非中国大陆）",
    )

    args = parser.parse_args()
    dispatch = {
        "export-cspm": cmd_export_cspm,
        "export-system-warning": cmd_export_system_warning,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
