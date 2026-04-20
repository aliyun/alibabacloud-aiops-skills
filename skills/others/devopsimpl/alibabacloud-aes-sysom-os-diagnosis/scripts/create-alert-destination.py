#!/usr/bin/env python3
"""
SysOM 告警联系人创建脚本

功能：通过 SDK 创建钉钉告警联系人（Alert Destination）
用法：python scripts/create-alert-destination.py <webhook_url> [destination_name]

参数：
  webhook_url        钉钉群机器人 Webhook 地址（必填）
  destination_name   告警联系人名称（可选，默认自动生成）

凭据来源（按优先级）：
  1. 环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. aliyun CLI 配置文件 ~/.aliyun/config.json（自动读取当前 profile）

返回：
  成功时输出 destination_id（纯数字），供后续 create-alert-strategy 使用
"""

import json
import os
import sys
from datetime import datetime


def validate_arguments():
    if len(sys.argv) < 2:
        print("❌ 缺少必填参数：webhook_url", file=sys.stderr)
        print(f"用法：python {sys.argv[0]} <webhook_url> [destination_name]", file=sys.stderr)
        sys.exit(1)

    webhook_url = sys.argv[1]
    if not webhook_url.startswith("https://oapi.dingtalk.com/robot/send"):
        print("⚠️  Webhook 地址格式可能不正确，预期格式：https://oapi.dingtalk.com/robot/send?access_token=xxx", file=sys.stderr)

    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    destination_name = sys.argv[2] if len(sys.argv) > 2 else f"aliyun-aes-skills-destination-{timestamp}"

    return webhook_url, destination_name


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
    webhook_url, destination_name = validate_arguments()
    access_key_id, access_key_secret = validate_credentials()

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

    request = models.CreateAlertDestinationRequest(
        target="dingtalk",
        name=destination_name,
        source="aes-skills",
        params=models.CreateAlertDestinationRequestParams(
            webhook=webhook_url
        )
    )

    try:
        response = client.create_alert_destination(request)
        response_body = response.body

        if hasattr(response_body, "to_map"):
            result = response_body.to_map()
        else:
            result = {"body": str(response_body)}

        code = result.get("code", "")
        if code == "Success":
            data = result.get("data", {})
            destination_id = data.get("id")
            print(destination_id)
            print(f"✅ 告警联系人创建成功", file=sys.stderr)
            print(f"   ID: {destination_id}", file=sys.stderr)
            print(f"   名称: {destination_name}", file=sys.stderr)
            print(f"   目标: dingtalk", file=sys.stderr)
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
