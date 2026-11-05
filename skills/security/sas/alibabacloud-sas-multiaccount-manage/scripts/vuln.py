#!/usr/bin/env python3
"""vuln.py — 云安全中心漏洞批量导出工具

用法:
  uv run vuln.py export-cve              # Linux 软件漏洞
  uv run vuln.py export-sys              # Windows 系统漏洞
  uv run vuln.py export-app              # 应用漏洞（含 SCA）
  uv run vuln.py export-emg              # 应急漏洞
  uv run vuln.py export-all              # 依次导出全部四种类型

  # 仅导出指定账号
  uv run vuln.py export-cve --account-id 1234567890
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

sys.path.insert(0, str(Path(__file__).parent))
from accounts import get_caller_account_id, get_enabled_accounts, load_accounts  # noqa: E402
from merge import merge_excel  # noqa: E402
from skill_meta import build_user_agent_header  # noqa: E402

TODAY = date.today().strftime("%Y%m%d")
QPS_LIMIT = 5
ALIYUN_USER_AGENT_HEADER = build_user_agent_header()
CLI_CONNECT_TIMEOUT_SECONDS = 10
CLI_READ_TIMEOUT_SECONDS = 60
DOWNLOAD_TIMEOUT_SECONDS = 60

_api_sem = None  # 在事件循环内初始化

# 当前凭证的主账号 ID，在 do_export() 中初始化
_caller_account_id = ""

# SAS API 地域，在 do_export() 中初始化
_region_id = "cn-shanghai"

_SKIP_ERROR_CODES = {"FreeVersionNotPermit", "NoPermission", "Forbidden"}

# ────────────────────────────── 导出类型配置 ──────────────────────────────

EXPORT_CONFIGS = {
    "cve": {
        "cli_args": [
            "--Lang", "zh",
            "--Type", "cve",
            "--Necessity", "asap,later,nntf",
            "--Dealed", "n",
        ],
        "prefix": "vul-cve",
        "desc": "Linux 软件漏洞",
    },
    "sys": {
        "cli_args": [
            "--Lang", "zh",
            "--Type", "sys",
            "--Necessity", "asap,later,nntf",
            "--Dealed", "n",
        ],
        "prefix": "vul-sys",
        "desc": "Windows 系统漏洞",
    },
    "app": {
        "cli_args": [
            "--Lang", "zh",
            "--Type", "app",
            "--Necessity", "asap,later,nntf",
            "--AttachTypes", "sca",
            "--AssetType", "ECS,CONTAINER",
            "--Dealed", "n",
        ],
        "prefix": "vul-app",
        "desc": "应用漏洞",
    },
    "emg": {
        "cli_args": [
            "--Lang", "zh",
            "--Type", "emg",
            "--RiskStatus", "y",
            "--Dealed", "n",
        ],
        "prefix": "vul-emg",
        "desc": "应急漏洞",
    },
}


# ────────────────────────────── 异常 ──────────────────────────────


class AccountSkippedError(Exception):
    """账号因权限不足等原因被跳过，不中断整体流程。"""

    def __init__(self, account_id, reason):
        self.account_id = account_id
        self.reason = reason
        super().__init__(f"账号 {account_id} 跳过: {reason}")


# ────────────────────────────── 异步 API 封装 ──────────────────────────────


async def _run_aliyun_async(args, account_id=""):
    """异步运行 aliyun CLI，通过信号量将并发 API 调用限制在 QPS ≤ 5。"""
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
        for code in _SKIP_ERROR_CODES:
            if code in err_text:
                raise AccountSkippedError(account_id, code)
        print(f"aliyun CLI 调用失败:\n{err_text}", file=sys.stderr)
        raise RuntimeError(f"aliyun CLI error: {err_text.strip()}")
    # returncode==0 但 stderr 中仍含可跳过错误码时也忽略
    for code in _SKIP_ERROR_CODES:
        if code in err_text:
            raise AccountSkippedError(account_id, code)
    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError:
        print(f"响应解析失败:\n{stdout.decode()}", file=sys.stderr)
        raise


async def start_export_async(vul_type, account_id):
    """发起漏洞导出任务，返回 export_id。"""
    cli_args = ["ExportVul", "--force"] + EXPORT_CONFIGS[vul_type]["cli_args"]
    if account_id != _caller_account_id:
        cli_args += ["--ResourceDirectoryAccountId", str(account_id)]

    data = await _run_aliyun_async(cli_args, account_id)
    print(f"  [提交] 账号 {account_id}，export_id={data['Id']}")
    return str(data["Id"])


async def wait_for_export_async(export_id, account_id, poll_interval=5):
    """轮询 DescribeVulExportInfo，成功后返回下载链接。"""
    while True:
        cli_args = [
            "DescribeVulExportInfo",
            "--force",
            "--ExportId", export_id,
        ]
        if account_id != _caller_account_id:
            cli_args += ["--ResourceDirectoryAccountId", str(account_id)]
        data = await _run_aliyun_async(cli_args, account_id)
        status = data.get("ExportStatus", "")
        if status == "success":
            return data["Link"]
        if status in ("failed", "error"):
            raise RuntimeError(f"账号 {account_id} 导出失败，状态={status}")
        await asyncio.sleep(poll_interval)


async def download_and_extract_async(link, account_id, prefix):
    """下载 zip，解压，重命名为 {prefix}-{account_id}-{date}.xlsx。"""
    zip_path = Path(f"{prefix}-{account_id}-{TODAY}.zip")
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


async def _wait_and_download(export_id, account_id, prefix, display_name=""):
    link = await wait_for_export_async(export_id, account_id)
    xlsx_path = await download_and_extract_async(link, account_id, prefix)
    return {"filename": xlsx_path, "account_id": account_id, "display_name": display_name}


# ────────────────────────────── 导出流程 ──────────────────────────────


async def do_export_async(vul_type, account_ids, account_display_names=None):
    """单类型并发导出：提交 → 等待 → 下载 → 合并 → 清理临时文件。"""
    global _api_sem
    _api_sem = asyncio.Semaphore(QPS_LIMIT)

    config = EXPORT_CONFIGS[vul_type]
    prefix = config["prefix"]
    merged_name = f"{prefix}-merged-{TODAY}.xlsx"
    _display_names = account_display_names or {}

    print(f"导出【{config['desc']}】共 {len(account_ids)} 个账号（耗时操作，请耐心等待）")

    # 阶段 1：并发提交
    submit_results = await asyncio.gather(
        *[start_export_async(vul_type, aid) for aid in account_ids],
        return_exceptions=True,
    )

    pending = []
    for aid, res in zip(account_ids, submit_results):
        if isinstance(res, AccountSkippedError):
            print(f"  [跳过][提交阶段] 账号 {aid}: {res.reason}", file=sys.stderr)
        elif isinstance(res, BaseException):
            print(f"  [失败] 账号 {aid}: {res}", file=sys.stderr)
        else:
            pending.append((res, aid))

    if not pending:
        print(f"所有账号导出任务均未成功提交，跳过【{config['desc']}】")
        return

    # 阶段 2：并发等待 + 下载
    download_results = await asyncio.gather(
        *[_wait_and_download(eid, aid, prefix, _display_names.get(str(aid), "")) for eid, aid in pending],
        return_exceptions=True,
    )

    inputs = []
    for (_, aid), res in zip(pending, download_results):
        if isinstance(res, AccountSkippedError):
            print(f"  [跳过][下载阶段] 账号 {aid}: {res.reason}", file=sys.stderr)
        elif isinstance(res, BaseException):
            print(f"  [失败] 账号 {aid}: {res}", file=sys.stderr)
        else:
            print(f"  [成功] 账号 {aid}")
            inputs.append(res)

    if not inputs:
        print(f"没有成功下载的文件，跳过【{config['desc']}】合并")
        return

    # 阶段 3：合并
    merge_excel(merged_name, inputs)

    # 阶段 4：清理临时文件
    for item in inputs:
        p = Path(item["filename"])
        if p.exists():
            p.unlink()
    print(f"已生成: {merged_name}（共 {len(inputs)} 个账号，已清理临时文件）")


def do_export(vul_type, account_ids, region_id="cn-shanghai", account_display_names=None):
    global _caller_account_id, _region_id
    _caller_account_id = get_caller_account_id()
    _region_id = region_id
    asyncio.run(do_export_async(vul_type, account_ids, account_display_names))


# ────────────────────────────── CLI ──────────────────────────────


def _get_account_infos(args):
    """Returns (account_ids, account_display_names dict)."""
    all_accounts = load_accounts()
    account_display_names = {str(a["AccountId"]): a.get("DisplayName", "") for a in all_accounts}
    if getattr(args, "account_id", None):
        return [args.account_id], account_display_names
    accounts = [a for a in all_accounts if a.get("enable", True)]
    if not accounts:
        print("错误: 没有可用账号，请先执行 accounts.py refresh", file=sys.stderr)
        sys.exit(1)
    return [a["AccountId"] for a in accounts], account_display_names


def cmd_export_cve(args):
    ids, names = _get_account_infos(args)
    do_export("cve", ids, args.region_id, names)


def cmd_export_sys(args):
    ids, names = _get_account_infos(args)
    do_export("sys", ids, args.region_id, names)


def cmd_export_app(args):
    ids, names = _get_account_infos(args)
    do_export("app", ids, args.region_id, names)


def cmd_export_emg(args):
    ids, names = _get_account_infos(args)
    do_export("emg", ids, args.region_id, names)


def cmd_export_all(args):
    ids, names = _get_account_infos(args)
    failed = []
    for vul_type in EXPORT_CONFIGS:
        try:
            do_export(vul_type, ids, args.region_id, names)
        except Exception as exc:
            failed.append(vul_type)
            print(f"导出【{EXPORT_CONFIGS[vul_type]['desc']}】失败: {exc}", file=sys.stderr)
    if failed:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="云安全中心漏洞批量导出工具")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    def _add_sub(name, help_text):
        p = sub.add_parser(name, help=help_text)
        p.add_argument(
            "--account-id",
            metavar="ACCOUNT_ID",
            help="指定单个账号 ID（默认导出所有启用账号）",
        )
        p.add_argument(
            "--region-id",
            dest="region_id",
            choices=["cn-shanghai", "ap-southeast-1"],
            default="cn-shanghai",
            help="SAS API 地域：cn-shanghai（中国大陆，默认）/ ap-southeast-1（非中国大陆）",
        )
        return p

    _add_sub("export-cve", "导出 Linux 软件漏洞（cve）")
    _add_sub("export-sys", "导出 Windows 系统漏洞（sys）")
    _add_sub("export-app", "导出应用漏洞（app，含 SCA）")
    _add_sub("export-emg", "导出应急漏洞（emg）")
    _add_sub("export-all", "依次导出全部四种漏洞类型")

    args = parser.parse_args()
    dispatch = {
        "export-cve": cmd_export_cve,
        "export-sys": cmd_export_sys,
        "export-app": cmd_export_app,
        "export-emg": cmd_export_emg,
        "export-all": cmd_export_all,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
