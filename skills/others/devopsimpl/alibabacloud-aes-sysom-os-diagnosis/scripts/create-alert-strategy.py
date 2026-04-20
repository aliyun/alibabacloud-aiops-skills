#!/usr/bin/env python3
"""
SysOM 告警策略创建脚本

功能：通过 SDK 创建告警策略（支持 destinations 参数，CLI 不支持此参数）
用法：.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
        --name <策略名称> \
        --items <告警项1>,<告警项2> \
        --clusters <集群1> \
        --destinations <联系人ID1>,<联系人ID2>

参数：
  --name          策略名称（必填）
  --items         告警项列表，逗号分隔（必填）
  --clusters      集群列表，逗号分隔（必填，实例模式填 default）
  --destinations  告警联系人 ID 列表，逗号分隔（必填）
  --k8s-label     是否启用 k8s 标签（可选，默认 false）

凭据来源（按优先级）：
  1. 环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. aliyun CLI 配置文件 ~/.aliyun/config.json（自动读取当前 profile）

返回：
  成功时 stdout 输出策略名称，详细信息输出到 stderr
"""

import argparse
import json
import os
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(description="创建 SysOM 告警策略")
    parser.add_argument("--name", required=True, help="策略名称")
    parser.add_argument("--items", required=True, help="告警项列表，逗号分隔")
    parser.add_argument("--clusters", required=True, help="集群列表，逗号分隔（实例模式填 default）")
    parser.add_argument("--destinations", required=True, help="告警联系人 ID 列表，逗号分隔")
    parser.add_argument("--k8s-label", action="store_true", default=False, help="是否启用 k8s 标签")
    return parser.parse_args()


def load_credentials_from_cli_config():
    config_path = os.path.join(os.path.expanduser("~"), ".aliyun", "config.json")
    if not os.path.exists(config_path):
        return None, None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        current_profile = config.get("current", "")
        profiles = config.get("profiles", [])

        target_profile = None
        for profile in profiles:
            if profile.get("name") == current_profile:
                target_profile = profile
                break

        if not target_profile and profiles:
            target_profile = profiles[0]

        if target_profile:
            access_key_id = target_profile.get("access_key_id", "")
            access_key_secret = target_profile.get("access_key_secret", "")
            if access_key_id and access_key_secret:
                profile_name = target_profile.get("name", "default")
                print(f"🔑 从 aliyun CLI 配置读取凭据（profile: {profile_name}）", file=sys.stderr)
                return access_key_id, access_key_secret
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return None, None

def validate_credentials():
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if access_key_id and access_key_secret:
        print("🔑 从环境变量读取凭据", file=sys.stderr)
        return access_key_id, access_key_secret

    access_key_id, access_key_secret = load_credentials_from_cli_config()
    if access_key_id and access_key_secret:
        return access_key_id, access_key_secret

    print("❌ 未找到阿里云凭据，请通过以下任一方式配置：", file=sys.stderr)
    print("   方式1：aliyun configure（推荐，脚本自动读取）", file=sys.stderr)
    print("   方式2：export ALIBABA_CLOUD_ACCESS_KEY_ID=<your_ak>", file=sys.stderr)
    print("          export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your_sk>", file=sys.stderr)
    sys.exit(1)


def main():
    args = parse_arguments()
    access_key_id, access_key_secret = validate_credentials()

    items_list = [item.strip() for item in args.items.split(",") if item.strip()]
    clusters_list = [cluster.strip() for cluster in args.clusters.split(",") if cluster.strip()]

    try:
        destinations_list = [int(d.strip()) for d in args.destinations.split(",") if d.strip()]
    except ValueError:
        print("❌ destinations 参数格式错误，应为逗号分隔的整数 ID（如：1,2,3）", file=sys.stderr)
        sys.exit(1)

    if not items_list:
        print("❌ 至少需要指定一个告警项（--items）", file=sys.stderr)
        sys.exit(1)

    if not destinations_list:
        print("❌ 至少需要指定一个告警联系人 ID（--destinations）", file=sys.stderr)
        sys.exit(1)

    try:
        from alibabacloud_tea_openapi.utils_models import Config
        from alibabacloud_sysom20231230.client import Client
        from alibabacloud_sysom20231230 import models
    except ImportError:
        print("❌ SDK 未安装，请先运行：bash scripts/setup-sdk.sh", file=sys.stderr)
        sys.exit(1)

    config = Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint="sysom.aliyuncs.com",
        user_agent="AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-os-diagnosis",
        connect_timeout=10000,
        read_timeout=30000
    )
    client = Client(config)

    strategy = models.CreateAlertStrategyRequestStrategy(
        clusters=clusters_list,
        items=items_list,
        destinations=destinations_list
    )

    request = models.CreateAlertStrategyRequest(
        name=args.name,
        enabled=True,
        k_8s_label=args.k8s_label,
        strategy=strategy
    )

    try:
        response = client.create_alert_strategy(request)
        response_body = response.body

        if hasattr(response_body, "to_map"):
            result = response_body.to_map()
        else:
            result = {"body": str(response_body)}

        code = result.get("code", "")
        if code == "Success":
            print(args.name)
            print(f"✅ 告警策略创建成功", file=sys.stderr)
            print(f"   策略名称: {args.name}", file=sys.stderr)
            print(f"   告警项数: {len(items_list)}", file=sys.stderr)
            print(f"   集群: {', '.join(clusters_list)}", file=sys.stderr)
            print(f"   告警联系人 ID: {destinations_list}", file=sys.stderr)
        else:
            message = result.get("message", "未知错误")
            print(f"❌ 创建失败：{code} - {message}", file=sys.stderr)
            print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

    except Exception as error:
        print(f"❌ API 调用异常：{error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
