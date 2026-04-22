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
from accounts import get_caller_account_id, get_enabled_accounts  # noqa: E402
from merge import merge_excel  # noqa: E402

TODAY = date.today().strftime("%Y%m%d")
QPS_LIMIT = 5
ALIYUN_USER_AGENT_HEADER = "User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-sas-multiaccount-manage"
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
            "--lang", "zh",
            "--type", "cve",
            "--necessity", "asap,later,nntf",
            "--dealed", "n",
        ],
        "prefix": "vul-cve",
        "desc": "Linux 软件漏洞",
    },
    "sys": {
        "cli_args": [
            "--lang", "zh",
            "--type", "sys",
            "--necessity", "asap,later,nntf",
            "--dealed", "n",
        ],
        "prefix": "vul-sys",
        "desc": "Windows 系统漏洞",
    },
    "app": {
        "cli_args": [
            "--lang", "zh",
            "--type", "app",
            "--necessity", "asap,later,nntf",
            "--attach-types", "sca",
            "--asset-type", "ECS,CONTAINER",
            "--dealed", "n",
        ],
        "prefix": "vul-app",
        "desc": "应用漏洞",
    },
    "emg": {
        "cli_args": [
            "--lang", "zh",
            "--type", "emg",
            "--risk-status", "y",
            "--dealed", "n",
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


async def start_export_async(vul_type, account_id):
    """发起漏洞导出任务，返回 export_id。"""
    cli_args = ["export-vul", "--force"] + EXPORT_CONFIGS[vul_type]["cli_args"]
    if account_id != _caller_account_id:
        cli_args += ["--resource-directory-account-id", str(account_id)]

    data = await _run_aliyun_async(cli_args, account_id)
    print(f"  [提交] 账号 {account_id}，export_id={data['Id']}")
    return str(data["Id"])


async def wait_for_export_async(export_id, account_id, poll_interval=5):
    """轮询 describe-vul-export-info，成功后返回下载链接。"""
    while True:
        cli_args = [
            "describe-vul-export-info",
            "--force",
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


async def _wait_and_download(export_id, account_id, prefix):
    link = await wait_for_export_async(export_id, account_id)
    xlsx_path = await download_and_extract_async(link, account_id, prefix)
    return {"filename": xlsx_path, "account_id": account_id}


# ────────────────────────────── 导出流程 ──────────────────────────────


async def do_export_async(vul_type, account_ids):
    """单类型并发导出：提交 → 等待 → 下载 → 合并 → 清理临时文件。"""
    global _api_sem
    _api_sem = asyncio.Semaphore(QPS_LIMIT)

    config = EXPORT_CONFIGS[vul_type]
    prefix = config["prefix"]
    merged_name = f"{prefix}-merged-{TODAY}.xlsx"

    print(f"导出【{config['desc']}】共 {len(account_ids)} 个账号（耗时操作，请耐心等待）")

    # 阶段 1：并发提交
    submit_results = await asyncio.gather(
        *[start_export_async(vul_type, aid) for aid in account_ids],
        return_exceptions=True,
    )

    pending = []
    skipped = []
    for aid, res in zip(account_ids, submit_results):
        if isinstance(res, AccountSkippedError):
            skipped.append(aid)
        elif isinstance(res, BaseException):
            print(f"  [失败] 账号 {aid}: {res}", file=sys.stderr)
        else:
            pending.append((res, aid))

    if not pending:
        print(f"所有账号均被跳过（{len(skipped)} 个），跳过【{config['desc']}】")
        return

    # 阶段 2：并发等待 + 下载
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


def do_export(vul_type, account_ids, region_id="cn-shanghai"):
    global _caller_account_id, _region_id
    _caller_account_id = get_caller_account_id()
    _region_id = region_id
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_export_async(vul_type, account_ids))


# ────────────────────────────── CLI ──────────────────────────────


def _get_account_ids(args):
    if getattr(args, "account_id", None):
        return [args.account_id]
    accounts = get_enabled_accounts()
    if not accounts:
        print("错误: 没有可用账号，请先执行 accounts.py refresh", file=sys.stderr)
        sys.exit(1)
    return [a["AccountId"] for a in accounts]


def cmd_export_cve(args):
    do_export("cve", _get_account_ids(args), args.region_id)


def cmd_export_sys(args):
    do_export("sys", _get_account_ids(args), args.region_id)


def cmd_export_app(args):
    do_export("app", _get_account_ids(args), args.region_id)


def cmd_export_emg(args):
    do_export("emg", _get_account_ids(args), args.region_id)


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

    args = parser.parse_args()
    dispatch = {
        "export-cve": cmd_export_cve,
        "export-sys": cmd_export_sys,
        "export-app": cmd_export_app,
        "export-emg": cmd_export_emg,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
