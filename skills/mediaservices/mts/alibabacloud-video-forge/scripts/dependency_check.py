#!/usr/bin/env python3
"""
dependency_check.py - 依赖包检查工具

用于检查脚本所需的依赖包是否已正确安装，
并在缺失时提供清晰的安装指导。
"""

import sys
import importlib.util

def check_package(package_name, install_name=None):
    """
    检查单个包是否已安装
    
    Args:
        package_name (str): Python包名
        install_name (str): pip安装时的名称（如果不同）
    
    Returns:
        bool: 包是否存在
    """
    if importlib.util.find_spec(package_name) is not None:
        return True
    else:
        install_cmd = install_name or package_name
        print(f"❌ 缺少依赖包: {package_name}", file=sys.stderr)
        print(f"   安装命令: pip install {install_cmd}", file=sys.stderr)
        return False

def check_required_packages(packages_dict):
    """
    检查多个必需包
    
    Args:
        packages_dict (dict): {package_name: install_name} 格式的字典
    
    Returns:
        bool: 所有包都存在返回True，否则返回False
    """
    missing_packages = []
    
    for package_name, install_name in packages_dict.items():
        if not check_package(package_name, install_name):
            missing_packages.append((package_name, install_name))
    
    if missing_packages:
        print("\n💡 完整安装命令:", file=sys.stderr)
        install_list = [name for _, name in missing_packages]
        print(f"   pip install {' '.join(install_list)}", file=sys.stderr)
        print("   # 或者如果权限不足:", file=sys.stderr)
        print(f"   pip install --user {' '.join(install_list)}", file=sys.stderr)
        return False
    
    return True

# 常用的阿里云相关包检查
ALICLOUD_PACKAGES = {
    'alibabacloud_mts20140618': 'alibabacloud-mts20140618',
    'alibabacloud_credentials': 'alibabacloud-credentials',
    'oss2': 'oss2'
}

def check_alicloud_dependencies():
    """检查阿里云相关的依赖包"""
    return check_required_packages(ALICLOUD_PACKAGES)

if __name__ == "__main__":
    # 测试依赖检查
    if check_alicloud_dependencies():
        print("✅ 所有阿里云依赖包均已安装")
        sys.exit(0)
    else:
        print("❌ 存在缺失的依赖包")
        sys.exit(1)