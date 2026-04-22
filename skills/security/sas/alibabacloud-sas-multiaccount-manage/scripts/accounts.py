#!/usr/bin/env python3
"""accounts.py — 多账号管理工具

用法:
  uv run accounts.py refresh
  uv run accounts.py search <DisplayName>
  uv run accounts.py enable <AccountId>
  uv run accounts.py disable <AccountId>
  uv run accounts.py list
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ACCOUNTS_FILE = Path("accounts.json")
ALIYUN_USER_AGENT_HEADER = "User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-sas-multiaccount-manage"
CLI_CONNECT_TIMEOUT_SECONDS = 10
CLI_READ_TIMEOUT_SECONDS = 60


def _aliyun_cmd(*args):
    """构建统一的 aliyun CLI 参数（含 User-Agent 与超时配置）。"""
    return [
        "aliyun",
        "--header",
        ALIYUN_USER_AGENT_HEADER,
        "--connect-timeout",
        str(CLI_CONNECT_TIMEOUT_SECONDS),
        "--read-timeout",
        str(CLI_READ_TIMEOUT_SECONDS),
        *args,
    ]


def load_accounts():
    if not ACCOUNTS_FILE.exists():
        print("错误: accounts.json 不存在，请先执行 refresh", file=sys.stderr)
        sys.exit(1)
    return json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))


def save_accounts(accounts):
    ACCOUNTS_FILE.write_text(
        json.dumps(accounts, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def cmd_refresh(args):
    """调用 aliyun sas list-accounts-in-resource-directory，写入 accounts.json"""
    region_id = getattr(args, "region_id", "cn-shanghai")

    # 获取当前凭证的主账号（自身也应包含在可操作范围内）
    identity_result = subprocess.run(
        _aliyun_cmd("sts", "get-caller-identity"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if identity_result.returncode != 0:
        print(f"get-caller-identity 调用失败:\n{identity_result.stderr}", file=sys.stderr)
        sys.exit(1)
    caller_account_id = str(json.loads(identity_result.stdout)["AccountId"])

    result = subprocess.run(
        _aliyun_cmd("sas", "--region", region_id, "list-accounts-in-resource-directory"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if result.returncode != 0:
        print(f"aliyun CLI 调用失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    accounts = data.get("Accounts", [])

    # 调用 describe-monitor-accounts，只保留已纳入监控的账号（并将自身主账号也包含进来）
    monitor_result = subprocess.run(
        _aliyun_cmd("sas", "--region", region_id, "describe-monitor-accounts"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if monitor_result.returncode != 0:
        print(f"describe-monitor-accounts 调用失败:\n{monitor_result.stderr}", file=sys.stderr)
        sys.exit(1)

    monitor_data = json.loads(monitor_result.stdout)
    monitored_ids = set(str(i) for i in monitor_data.get("AccountIds", []))
    monitored_ids.add(caller_account_id)  # 自身主账号始终属于可操作范围

    accounts = [a for a in accounts if str(a["AccountId"]) in monitored_ids]

    # 保留已有的 enable 状态，新账号默认 enable=true
    existing = {}
    if ACCOUNTS_FILE.exists():
        for a in json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8")):
            existing[a["AccountId"]] = a.get("enable", True)

    for account in accounts:
        account["enable"] = existing.get(account["AccountId"], True)

    save_accounts(accounts)
    print(f"已刷新 {len(accounts)} 个账号，写入 {ACCOUNTS_FILE}")


def cmd_search(args):
    """按 DisplayName 模糊搜索，输出 AccountId"""
    keyword = args.keyword.lower()
    accounts = load_accounts()
    results = [
        a for a in accounts if keyword in a.get("DisplayName", "").lower()
    ]
    if not results:
        print(f"未找到匹配 '{args.keyword}' 的账号")
        return
    for a in results:
        status = "启用" if a.get("enable", True) else "禁用"
        print(f"{a['AccountId']}\t{a.get('DisplayName', '')}\t[{status}]")


def _set_enable(account_id, value):
    accounts = load_accounts()
    found = False
    for a in accounts:
        if a["AccountId"] == account_id:
            a["enable"] = value
            found = True
            break
    if not found:
        print(f"错误: 未找到账号 {account_id}", file=sys.stderr)
        sys.exit(1)
    save_accounts(accounts)
    action = "启用" if value else "禁用"
    print(f"账号 {account_id} 已{action}")


def cmd_enable(args):
    _set_enable(args.account_id, True)


def cmd_disable(args):
    _set_enable(args.account_id, False)


def cmd_list(_args):
    """列出所有账号"""
    accounts = load_accounts()
    for a in accounts:
        status = "启用" if a.get("enable", True) else "禁用"
        print(f"{a['AccountId']}\t{a.get('DisplayName', ''):<20}\t[{status}]")


def get_enabled_accounts():
    """供其他模块调用：返回所有 enable=True 的账号列表"""
    return [a for a in load_accounts() if a.get("enable", True)]


def get_caller_account_id():
    """获取当前凭证的主账号 ID（通过 aliyun sts get-caller-identity）。"""
    result = subprocess.run(
        _aliyun_cmd("sts", "get-caller-identity"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if result.returncode != 0:
        print(f"get-caller-identity 调用失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return str(json.loads(result.stdout)["AccountId"])


def main():
    parser = argparse.ArgumentParser(
        description="阿里云云安全中心多账号管理工具"
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    p_refresh = sub.add_parser("refresh", help="刷新账号列表（从资源目录拉取）")
    p_refresh.add_argument(
        "--region-id",
        dest="region_id",
        choices=["cn-shanghai", "ap-southeast-1"],
        default="cn-shanghai",
        help="SAS API 地域：cn-shanghai（中国大陆，默认）/ ap-southeast-1（非中国大陆）",
    )

    p_search = sub.add_parser("search", help="按 DisplayName 搜索账号")
    p_search.add_argument("keyword", help="搜索关键字")

    p_enable = sub.add_parser("enable", help="启用指定账号")
    p_enable.add_argument("account_id", help="账号 ID")

    p_disable = sub.add_parser("disable", help="禁用指定账号")
    p_disable.add_argument("account_id", help="账号 ID")

    sub.add_parser("list", help="列出所有账号及状态")

    args = parser.parse_args()
    dispatch = {
        "refresh": cmd_refresh,
        "search": cmd_search,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "list": cmd_list,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
