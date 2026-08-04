#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import configparser
import csv
import sys
import os
from urllib.parse import urlparse

def read_config(config_path):
    """读取并验证配置文件"""
    config = configparser.ConfigParser()
    if not config.read(config_path):
        print(f"错误：无法读取配置文件 '{config_path}'。")
        sys.exit(1)
    
    required_sections = {
        'rclone_source_hdfs': ['name', 'namenode', 'username'],
        'rclone_target_s3': ['name', 'provider', 'endpoint', 'access_key_id', 'secret_access_key', 'bucket'],
        'rclone_options': ['copy_flags', 'bwlimit']
    }

    for section, keys in required_sections.items():
        if not config.has_section(section):
            print(f"错误：配置文件 '{config_path}' 中缺少必需的 '[{section}]' 部分。")
            sys.exit(1)
        for key in keys:
            if not config.has_option(section, key):
                print(f"错误：'[{section}]' 部分中缺少必需的键 '{key}'。")
                sys.exit(1)
    
    print("配置文件读取成功。")
    return config

def generate_rclone_config_commands(config):
    """根据配置生成 rclone config create 命令，不带双引号"""
    commands = []
    
    # HDFS Source
    src_cfg = config['rclone_source_hdfs']
    src_name = src_cfg['name']
    commands.append(f"# --- 配置 HDFS 源: {src_name} ---")
    # CHANGE 3: Removed double quotes from config values
    commands.append(
        f"rclone config create {src_name} hdfs "
        f"namenode {src_cfg['namenode']} "
        f"username {src_cfg['username']}"
    )
    commands.append("")

    # S3 Target
    tgt_cfg = config['rclone_target_s3']
    tgt_name = tgt_cfg['name']
    commands.append(f"# --- 配置 S3 目标: {tgt_name} ---")
    # CHANGE 3: Removed double quotes from config values
    commands.append(
        f"rclone config create {tgt_name} s3 "
        f"provider {tgt_cfg['provider']} "
        f"endpoint {tgt_cfg['endpoint']} "
        f"access_key_id {tgt_cfg['access_key_id']} "
        f"secret_access_key {tgt_cfg['secret_access_key']}"
    )
    commands.append("\n# === 同步命令开始 ===\n")
    
    return commands

def process_changes_and_generate_commands(csv_path, config):
    """
    处理CSV文件，生成rclone copy命令和结构变更列表。
    """
    copy_commands = []
    schema_changes = set() # 使用set避免重复记录

    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            src_name = config.get('rclone_source_hdfs', 'name')
            tgt_name = config.get('rclone_target_s3', 'name')
            tgt_bucket = config.get('rclone_target_s3', 'bucket')
            copy_flags = config.get('rclone_options', 'copy_flags')
            bwlimit = config.get('rclone_options', 'bwlimit')
            
            copy_event_types = {
                'TABLE_CREATE', 
                'PARTITION_CREATE', 
                'DATA_MODIFIED', 
                'PARTITION_MODIFIED'
            }

            for row in reader:
                event_type = row.get('type')
                location = row.get('location')

                if event_type in copy_event_types:
                    if not location:
                        print(f"警告：跳过记录，因为 location 为空: {row}")
                        continue
                    
                    try:
                        parsed_url = urlparse(location)
                        source_path = parsed_url.path
                        if not source_path:
                            print(f"警告：无法从 location '{location}' 解析路径，跳过。")
                            continue
                    except Exception as e:
                        print(f"警告：解析 location '{location}' 时出错: {e}，跳过。")
                        continue
                    
                    target_path = source_path
                    
                    # 构建 rclone copy 命令
                    command = (
                        f'rclone copy {copy_flags} --bwlimit "{bwlimit}" '
                        f'{src_name}:{source_path} '
                        f'{tgt_name}:{tgt_bucket}{target_path}'
                    )
                    copy_commands.append(command)

                elif event_type == 'TABLE_MODIFIED':
                    db_name = row.get('db_name')
                    table_name = row.get('table_name')
                    if db_name and table_name:
                        schema_changes.add(f"{db_name}.{table_name}")

    except FileNotFoundError:
        print(f"错误：输入文件 '{csv_path}' 未找到。")
        sys.exit(1)
    except Exception as e:
        print(f"处理CSV文件时发生未知错误: {e}")
        sys.exit(1)
        
    return copy_commands, list(schema_changes)


def main():
    parser = argparse.ArgumentParser(
        description="根据元数据变更CSV文件生成 rclone 同步脚本。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-c", "--config",
        default="config.ini",
        help="配置文件的路径 (默认: config.ini)"
    )
    parser.add_argument(
        "-i", "--input-csv",
        default="metastore_delta.csv",
        help="输入的元数据变更CSV文件 (默认: metastore_delta.csv)"
    )
    parser.add_argument(
        "--output-script",
        default="sync_commands.sh",
        help="生成的 rclone 命令脚本文件 (默认: sync_commands.sh)"
    )
    parser.add_argument(
        "--output-schema-changes",
        default="schema_changes.txt",
        help="记录表结构变更的输出文件 (默认: schema_changes.txt)"
    )
    
    args = parser.parse_args()

    # 1. 读取和验证配置
    config = read_config(args.config)

    # 2. 生成 rclone config 命令
    config_commands = generate_rclone_config_commands(config)

    # 3. 处理CSV并生成 rclone copy 命令
    print(f"正在处理输入文件 '{args.input_csv}'...")
    copy_commands, schema_changes = process_changes_and_generate_commands(args.input_csv, config)
    print(f"发现 {len(copy_commands)} 个数据同步任务。")
    print(f"发现 {len(schema_changes)} 个表结构变更。")

    # 4. 写入 rclone 命令脚本
    try:
        with open(args.output_script, 'w', encoding='utf-8') as f:
            f.write("#!/bin/bash\n")
            # CHANGE 1: Updated auto-generated comment to reflect new script name
            f.write("# Auto-generated by generate_rclone_script.py\n\n")
            
            # CHANGE 2: Removed 'set -e' from the script output
            # f.write("set -e\n\n")

            for command in config_commands:
                f.write(command + '\n')
            
            for command in copy_commands:
                f.write(command + '\n')

        print(f"Rclone 命令已成功写入到脚本: '{args.output_script}'")

    except IOError as e:
        print(f"错误：无法写入脚本文件 '{args.output_script}': {e}")
        sys.exit(1)

    # 5. 写入表结构变更列表
    if schema_changes:
        try:
            with open(args.output_schema_changes, 'w', encoding='utf-8') as f:
                f.write("# Tables with schema modifications (TABLE_MODIFIED)\n")
                f.write("# These tables may require manual DDL synchronization.\n\n")
                for table in sorted(schema_changes):
                    f.write(table + '\n')
            print(f"表结构变更列表已写入到: '{args.output_schema_changes}'")
        except IOError as e:
            print(f"错误：无法写入结构变更文件 '{args.output_schema_changes}': {e}")
            sys.exit(1)

    print("\n脚本执行完毕。")


if __name__ == "__main__":
    main()
