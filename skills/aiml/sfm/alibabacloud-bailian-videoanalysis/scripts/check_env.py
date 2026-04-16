#!/usr/bin/env python3
"""
Check the Bailian SDK environment and credential configuration.
Returns a JSON object with the check results.
Uses the Alibaba Cloud default credential chain; does not directly read AccessKey/SecretKey.
"""

import subprocess
import json
import sys

try:
    from alibabacloud_credentials.client import Client as CredentialClient
except ImportError:
    CredentialClient = None

# 必要的 Python 依赖列表
REQUIRED_PACKAGES = [
    'alibabacloud-bailian20231229',
    'alibabacloud-quanmiaolightapp20240801',
    'alibabacloud-openapi-util',
    'alibabacloud-credentials',
    'alibabacloud-tea-openapi',
    'alibabacloud-tea-util'
]

def check_package_installed(package_name):
    """检查 Python 包是否已安装"""
    try:
        subprocess.run(
            ['pip', 'show', package_name],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_env():
    result = {
        'pythonPackagesInstalled': {},
        'allPythonPackagesInstalled': False,
        'credentialsConfigured': False,
        'ready': False,
        'errors': []
    }

    # 检查凭证是否可通过默认凭证链获取
    try:
        if CredentialClient is None:
            raise ImportError('alibabacloud-credentials 未安装')
        credential = CredentialClient()
        # 尝试获取凭证，验证凭证链是否可用
        credential.get_credential().access_key_id
        result['credentialsConfigured'] = True
    except Exception as error:
        result['errors'].append('阿里云凭证未配置，请运行 `aliyun configure` 配置凭证')
        result['credentialsConfigured'] = False

    # 检查所有必要的 Python 包是否安装
    all_installed = True
    for pkg in REQUIRED_PACKAGES:
        if check_package_installed(pkg):
            result['pythonPackagesInstalled'][pkg] = True
        else:
            result['pythonPackagesInstalled'][pkg] = False
            result['errors'].append(f'未安装 Python 包：{pkg}')
            all_installed = False
    
    result['allPythonPackagesInstalled'] = all_installed

    # 判断是否就绪
    result['ready'] = result['credentialsConfigured'] and result['allPythonPackagesInstalled']

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    check_env()
