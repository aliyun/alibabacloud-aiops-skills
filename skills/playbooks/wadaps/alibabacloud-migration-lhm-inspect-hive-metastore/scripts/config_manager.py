#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理模块

提供 profile 存储/加载、CLI 参数合并、交互式配置补全等能力。
"""

import configparser
import getpass
import os
import sys

PROFILE_DIR = os.path.expanduser("~/.hive_explore/profiles")

# 配置 schema：定义各 section 的键、默认值、是否必填、交互提示
CONFIG_SCHEMA = {
    'general': {
        'connection_mode': {'default': 'thrift', 'required': False, 'prompt': '连接模式 (db/thrift/both)'},
        'fallback_host': {'default': '', 'required': False, 'prompt': '备用主机 (内网不通时回退)'},
    },
    'thrift': {
        'host': {'default': None, 'required': True, 'prompt': 'HMS Thrift 主机地址'},
        'port': {'default': '9083', 'required': False, 'prompt': 'Thrift 端口'},
        'auth': {'default': 'NOSASL', 'required': False, 'prompt': '认证方式 (NOSASL/KERBEROS)'},
        'kerberos_principal': {'default': '', 'required': False, 'prompt': 'Kerberos 主体'},
        'timeout': {'default': '60', 'required': False, 'prompt': '连接超时(秒)'},
        'size_source': {'default': 'params', 'required': False, 'prompt': '表大小获取 (params/hadoop/skip)'},
    },
    'metastore_db': {
        'db_type': {'default': 'mysql', 'required': False, 'prompt': '数据库类型 (mysql/postgres)'},
        'host': {'default': None, 'required': True, 'prompt': 'Metastore DB 主机'},
        'port': {'default': '3306', 'required': False, 'prompt': 'DB 端口'},
        'user': {'default': None, 'required': True, 'prompt': 'DB 用户名'},
        'password': {'default': None, 'required': True, 'prompt': 'DB 密码', 'secret': True},
        'database': {'default': '', 'required': False, 'prompt': 'Metastore 数据库名 (留空自动检测)'},
    },
}

# CLI 参数名 → (section, key) 的映射
_CLI_ARG_MAP = {
    'host': [('metastore_db', 'host'), ('thrift', 'host')],
    'thrift_host': [('thrift', 'host')],
    'port': [('metastore_db', 'port')],
    'thrift_port': [('thrift', 'port')],
    'user': [('metastore_db', 'user')],
    'password': [('metastore_db', 'password')],
    'database': [('metastore_db', 'database')],
    'db_type': [('metastore_db', 'db_type')],
    'auth': [('thrift', 'auth')],
    'mode': [('general', 'connection_mode')],
    'fallback_host': [('general', 'fallback_host')],
}


def list_profiles():
    """返回已保存的 profile 名称列表"""
    if not os.path.isdir(PROFILE_DIR):
        return []
    return sorted([
        f[:-4] for f in os.listdir(PROFILE_DIR)
        if f.endswith('.ini') and not f.startswith('.')
    ])


def expand_env_vars(config):
    """
    对 ConfigParser 中的所有值做 ${ENV_VAR} / $ENV_VAR 展开。
    未定义的环境变量保留原文（交由下游的占位符校验逻辑识别）。
    原地修改并返回同一对象，方便链式调用。
    """
    for section in config.sections():
        for key, val in config.items(section):
            if val and '$' in val:
                config.set(section, key, os.path.expandvars(val))
    return config


def load_profile(name):
    """
    加载已保存的 profile。

    返回:
        configparser.ConfigParser
    """
    path = os.path.join(PROFILE_DIR, f"{name}.ini")
    if not os.path.exists(path):
        available = list_profiles()
        avail_str = ', '.join(available) if available else '(无)'
        raise FileNotFoundError(
            f"Profile '{name}' 不存在。可用: {avail_str}"
        )
    config = configparser.ConfigParser()
    config.read(path, encoding='utf-8')
    expand_env_vars(config)
    return config


def save_profile(name, config):
    """
    保存配置为 profile。

    参数:
        name: profile 名称
        config: ConfigParser 对象
    """
    os.makedirs(PROFILE_DIR, exist_ok=True)
    path = os.path.join(PROFILE_DIR, f"{name}.ini")
    with open(path, 'w', encoding='utf-8') as f:
        config.write(f)
    if name != '_last':
        print(f"  配置已保存到: {path}")
        # 安全提示
        has_password = False
        for section in config.sections():
            if config.has_option(section, 'password') and config.get(section, 'password'):
                has_password = True
                break
        if has_password:
            print(f"  注意: 文件包含密码明文，建议执行: chmod 600 {path}")


def merge_cli_args_into_config(args, base_config=None):
    """
    将 CLI 参数合并到配置中（CLI 参数优先级高于文件）。

    参数:
        args: argparse.Namespace
        base_config: 基础 ConfigParser (可选)

    返回:
        configparser.ConfigParser
    """
    config = base_config if base_config else configparser.ConfigParser()

    # 确保所有需要的 section 存在
    for section in ('general', 'thrift', 'metastore_db'):
        if not config.has_section(section):
            config.add_section(section)

    args_dict = vars(args) if hasattr(args, '__dict__') else {}

    for arg_name, mappings in _CLI_ARG_MAP.items():
        value = args_dict.get(arg_name)
        if value is not None:
            for section, key in mappings:
                config.set(section, key, str(value))

    return config


def determine_required_sections(mode, task):
    """
    根据模式和任务确定需要哪些配置段。

    参数:
        mode: 'db', 'thrift', 'both'
        task: 'full', 'incr', 'test', 'compare'

    返回:
        list[str]: 需要的 section 名称列表
    """
    if task == 'compare' or mode == 'both':
        return ['metastore_db', 'thrift']
    elif mode == 'db':
        return ['metastore_db']
    else:
        return ['thrift']


def interactive_fill(config, required_sections, no_interactive=False):
    """
    交互式补全缺失的必填配置项。

    参数:
        config: ConfigParser 对象
        required_sections: 需要检查的 section 列表
        no_interactive: 禁用交互（非 TTY 或明确禁用）

    返回:
        ConfigParser (原地修改并返回)
    """
    is_tty = sys.stdin.isatty() and not no_interactive
    missing = []

    for section in required_sections:
        schema = CONFIG_SCHEMA.get(section, {})
        for key, spec in schema.items():
            if not spec.get('required', False):
                continue

            current = ''
            if config.has_option(section, key):
                current = config.get(section, key).strip()

            # 检查是否为占位符
            if current and not current.startswith('$') and current != 'your_':
                continue

            if not is_tty:
                missing.append(f"[{section}].{key}")
                continue

            # 交互提示
            prompt_text = spec.get('prompt', key)
            default = spec.get('default', '')
            if default:
                prompt_str = f"  {prompt_text} [{default}]: "
            else:
                prompt_str = f"  {prompt_text}: "

            while True:
                if spec.get('secret', False):
                    value = getpass.getpass(prompt_str)
                else:
                    value = input(prompt_str).strip()

                if not value and default:
                    value = str(default)

                if value:
                    if not config.has_section(section):
                        config.add_section(section)
                    config.set(section, key, value)
                    break
                else:
                    print(f"    此项为必填，请输入值")

    if missing:
        raise ValueError(
            f"以下必填配置项缺失（使用交互模式或 CLI 参数提供）:\n  "
            + '\n  '.join(missing)
        )

    return config


def config_to_dict(config, section):
    """将 ConfigParser 的某个 section 转换为字典"""
    if not config.has_section(section):
        return {}
    return dict(config.items(section))
