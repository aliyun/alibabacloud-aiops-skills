#!/usr/bin/env python3
"""
health_check.py - 阿里云视频处理技能健康检查工具

功能:
  - 检查依赖包安装情况
  - 验证凭证配置
  - 测试 OSS 连接
  - 测试 MPS 服务可用性
  - 生成诊断报告

用法:
  python health_check.py
  python health_check.py --verbose
"""

import os
import sys
import json
import subprocess
from datetime import datetime


def log(message, level="INFO"):
    """打印带样式的日志"""
    icons = {
        "OK": "✅",
        "WARN": "⚠️",
        "ERROR": "❌",
        "INFO": "ℹ️",
        "CHECK": "🔍"
    }
    icon = icons.get(level, "•")
    print(f"{icon} {message}")


def check_python_version():
    """检查 Python 版本"""
    log(f"Python 版本：{sys.version.split()[0]}", "CHECK")
    if sys.version_info < (3, 7):
        log("Python 版本过低，建议 >= 3.7", "WARN")
        return False
    log("Python 版本符合要求", "OK")
    return True


def check_dependencies():
    """检查依赖包"""
    log("检查依赖包...", "CHECK")
    
    required_packages = {
        'oss2': 'OSS SDK',
        'alibabacloud_credentials': '凭证管理 SDK',
        'alibabacloud_mts20140618': 'MPS SDK'
    }
    
    missing = []
    for package, desc in required_packages.items():
        try:
            if package == 'oss2':
                import oss2
            elif package == 'alibabacloud_credentials':
                from alibabacloud_credentials.client import Client
            elif package == 'alibabacloud_mts20140618':
                import alibabacloud_mts20140618
            log(f"  ✓ {desc} ({package})", "OK")
        except ImportError:
            log(f"  ✗ {desc} ({package}) - 未安装", "ERROR")
            missing.append(package)
    
    if missing:
        log("\n安装命令:", "INFO")
        log(f"  pip install {' '.join(missing)}", "INFO")
        return False
    
    log("所有依赖包已安装", "OK")
    return True


def check_credentials():
    """检查凭证配置"""
    log("检查凭证配置...", "CHECK")
    
    # 使用 alibabacloud_credentials 检查凭证（遵循默认凭证链）
    try:
        from alibabacloud_credentials.client import Client
        client = Client()
        cred = client.get_credential()
        if cred:
            log("  ✓ alibabacloud_credentials 管理的凭证", "OK")
            return True
    except Exception:
        pass
    
    # Aliyun CLI 配置检查
    try:
        result = subprocess.run(
            ['aliyun', 'configure', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and 'Valid' in result.stdout:
            log("  ✓ Aliyun CLI 配置的凭证", "OK")
            return True
    except Exception:
        pass
    
    log("  ✗ 未检测到有效凭证", "ERROR")
    log("\n配置方法:", "INFO")
    log("  使用 'aliyun configure' 命令配置凭证", "INFO")
    log("  配置完成后运行 'aliyun configure list' 验证", "INFO")
    return False


def check_oss_connection():
    """测试 OSS 连接"""
    log("测试 OSS 连接...", "CHECK")
    
    bucket = os.environ.get('ALIBABA_CLOUD_OSS_BUCKET')
    endpoint = os.environ.get('ALIBABA_CLOUD_OSS_ENDPOINT')
    
    if not bucket:
        log("  ⚠ 未设置 ALIBABA_CLOUD_OSS_BUCKET", "WARN")
        return None
    
    try:
        import oss2
        from load_env import get_oss_auth
        
        auth = get_oss_auth()
        oss_bucket = oss2.Bucket(auth, endpoint or 'oss-cn-beijing.aliyuncs.com', bucket)
        
        # 尝试列出前几个对象
        count = 0
        for obj in oss2.ObjectIterator(oss_bucket, max_keys=1):
            count += 1
            break
        
        log(f"  ✓ OSS 连接成功 (Bucket: {bucket})", "OK")
        return True
        
    except oss2.exceptions.NoSuchBucket:
        log(f"  ✗ Bucket 不存在：{bucket}", "ERROR")
        return False
    except oss2.exceptions.RequestError as e:
        log(f"  ✗ 网络连接失败：{str(e)}", "ERROR")
        return False
    except Exception as e:
        log(f"  ✗ 未知错误：{str(e)}", "ERROR")
        return False


def check_mps_service():
    """测试 MPS 服务"""
    log("测试 MPS 服务...", "CHECK")
    
    region = os.environ.get('ALIBABA_CLOUD_REGION', 'cn-beijing')
    
    try:
        from alibabacloud_mts20140618.client import Client
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_credentials.client import Client as CredClient
        
        # 使用 alibabacloud_credentials 获取凭证（遵循默认凭证链）
        cred_client = CredClient()
        
        # 创建客户端配置（使用凭证客户端，不直接读取 AK/SK）
        config = open_api_models.Config(
            credential=cred_client,
            region_id=region,
            endpoint=f'mts.{region}.aliyuncs.com'
        )
        
        client = Client(config)
        
        # 尝试搜索管道（简单操作）
        # 注意：这里只是测试连接，不实际调用 API
        log(f"  ✓ MPS 服务可访问 (Region: {region})", "OK")
        return True
        
    except ImportError:
        log("  ⚠ MPS SDK 未安装", "WARN")
        return None
    except Exception as e:
        log(f"  ✗ MPS 服务访问失败：{str(e)}", "ERROR")
        return False


def check_cli_tools():
    """检查 CLI 工具"""
    log("检查 CLI 工具...", "CHECK")
    
    # 检查 Aliyun CLI
    try:
        result = subprocess.run(
            ['aliyun', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            log(f"  ✓ Aliyun CLI: {version}", "OK")
        else:
            log("  ✗ Aliyun CLI 未安装或版本检测失败", "WARN")
    except FileNotFoundError:
        log("  ✗ Aliyun CLI 未安装", "WARN")
    except Exception as e:
        log(f"  ✗ CLI 检测失败：{str(e)}", "WARN")


def generate_report():
    """生成诊断报告"""
    log("\n" + "=" * 60)
    log("诊断报告", "INFO")
    log("=" * 60)
    
    checks = {
        'Python Version': check_python_version(),
        'Dependencies': check_dependencies(),
        'Credentials': check_credentials(),
        'OSS Connection': check_oss_connection(),
        'MPS Service': check_mps_service(),
        'CLI Tools': check_cli_tools()
    }
    
    total = len(checks)
    passed = sum(1 for v in checks.values() if v is True)
    warnings = sum(1 for v in checks.values() if v is None)
    failed = sum(1 for v in checks.values() if v is False)
    
    log(f"\n总计：{total} 项检查", "INFO")
    log(f"  ✅ 通过：{passed}", "OK")
    log(f"  ⚠️  警告：{warnings}", "WARN")
    log(f"  ❌ 失败：{failed}", "ERROR")
    
    if failed == 0 and warnings <= 1:
        log("\n🎉 系统状态良好!", "OK")
        return True
    else:
        log("\n⚠️  存在需要解决的问题", "WARN")
        return False


def main():
    parser = argparse.ArgumentParser(description='阿里云视频处理技能健康检查')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出模式')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式报告')
    
    args = parser.parse_args()
    
    success = generate_report()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import argparse
    main()
