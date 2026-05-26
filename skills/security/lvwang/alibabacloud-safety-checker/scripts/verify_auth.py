#!/usr/bin/env python3
"""
凭证链连通性验证 - 验证阿里云默认凭证链是否有效且有内容安全权限
"""
import os
import sys

def verify_auth():
    """验证默认凭证链并检查权限"""
    print("正在通过默认凭证链获取凭证...")

    try:
        from alibabacloud_green20220302.client import Client
        from alibabacloud_green20220302 import models
        from alibabacloud_tea_openapi.models import Config
        from alibabacloud_tea_util.models import RuntimeOptions
        from alibabacloud_credentials.client import Client as CredClient
    except ImportError:
        print("[ERROR] 缺少阿里云SDK依赖")
        print("请执行: pip install alibabacloud-green20220302 alibabacloud-credentials")
        return False

    try:
        cred = CredClient()
        print("✓ 默认凭证链初始化成功")
    except Exception as e:
        print(f"[ERROR] 默认凭证链初始化失败: {e}")
        print("支持的凭证方式:")
        print("  1. 环境变量（自动读取）")
        print("  2. 配置文件（~/.alibabacloud/credentials）")
        print("  3. ECS 实例 RAM 角色")
        return False

    print("\n正在验证连通性...")
    try:
        region = os.environ.get("CONTENT_SECURITY_REGION", "cn-shanghai")
        endpoint = f"green-cip.{region}.aliyuncs.com"

        config = Config(
            credential=cred,
            region_id=region,
            endpoint=endpoint,
            user_agent="AlibabaCloud-Agent-Skills/alibabacloud-safety-checker",
            read_timeout=30,
            connect_timeout=10,
        )
        client = Client(config)
        runtime = RuntimeOptions()

        # 发送一个简单的文本审核请求验证连通性
        request = models.TextModerationPlusRequest(
            service="ugc_moderation_byllm",
            service_parameters='{"content": "hello world"}',
        )

        response = client.text_moderation_plus_with_options(request, runtime)

        if response.status_code == 200:
            body = response.body
            print(f"✓ 验证成功！HTTP {response.status_code}")
            print(f"  Code: {body.code}")
            print(f"  RequestId: {body.request_id}")

            if body.code == 200:
                print(f"  审核结果: {body.data.risk_level if body.data else 'N/A'}")

            print("\n凭证有效，可以继续使用")
            return True
        else:
            print(f"[ERROR] 验证失败，HTTP {response.status_code}")
            print(f"  Response: {response.body}")
            return False

    except Exception as e:
        error_str = str(e)
        if "InvalidAccessKeyId" in error_str or "access key" in error_str.lower():
            print(f"[ERROR] 凭证无效: {error_str}")
            print("  请检查凭证链配置是否正确")
        elif "Forbidden" in error_str or "权限" in error_str:
            print(f"[ERROR] 权限不足: {error_str}")
            print("  请为 RAM 用户授予 AliyunYundunGreenWebFullAccess 权限")
        else:
            print(f"[ERROR] 验证异常: {error_str}")
            print("  请检查：")
            print("  1. 网络是否正常")
            print("  2. 内容安全服务是否已开通")
        return False


if __name__ == "__main__":
    success = verify_auth()
    sys.exit(0 if success else 1)
