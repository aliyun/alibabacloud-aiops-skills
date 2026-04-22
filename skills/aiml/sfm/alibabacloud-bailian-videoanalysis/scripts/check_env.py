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

# Required Python packages list
REQUIRED_PACKAGES = [
    'alibabacloud-quanmiaolightapp20240801',
    'alibabacloud-openapi-util',
    'alibabacloud-credentials',
    'alibabacloud-tea-openapi',
    'alibabacloud-tea-util'
]

def check_package_installed(package_name):
    """Check if Python package is installed using importlib.metadata (Python 3.8+)"""
    try:
        # Use importlib.metadata which is more reliable than pip commands
        from importlib.metadata import version
        version(package_name)
        return True
    except ImportError:
        # Fallback for older Python versions
        try:
            import pkg_resources
            pkg_resources.get_distribution(package_name)
            return True
        except (ImportError, pkg_resources.DistributionNotFound):
            return False
    except Exception:
        return False


def check_env():
    result = {
        'pythonPackagesInstalled': {},
        'allPythonPackagesInstalled': False,
        'credentialsConfigured': False,
        'ready': False,
        'errors': []
    }

    # Check if credentials can be obtained through default credential chain
    try:
        if CredentialClient is None:
            raise ImportError('alibabacloud-credentials not installed')
        credential = CredentialClient()
        # Try to get credentials to verify credential chain is available
        credential.get_credential().access_key_id
        result['credentialsConfigured'] = True
    except Exception as error:
        result['errors'].append('Alibaba Cloud credentials not configured, please run `aliyun configure` to configure credentials')
        result['credentialsConfigured'] = False

    # Check if all required Python packages are installed
    all_installed = True
    for pkg in REQUIRED_PACKAGES:
        if check_package_installed(pkg):
            result['pythonPackagesInstalled'][pkg] = True
        else:
            result['pythonPackagesInstalled'][pkg] = False
            result['errors'].append(f'Python package not installed: {pkg}')
            all_installed = False
    
    result['allPythonPackagesInstalled'] = all_installed

    # Determine if ready
    result['ready'] = result['credentialsConfigured'] and result['allPythonPackagesInstalled']

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    check_env()
