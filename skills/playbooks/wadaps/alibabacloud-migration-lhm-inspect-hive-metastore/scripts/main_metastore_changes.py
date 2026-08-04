#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import configparser
import sys
import subprocess
import os
from datetime import datetime  # 引入datetime模块

# --- 脚本常量配置 ---
GET_CHANGES_SCRIPT_DB = "get_metastore_changes.py"
GET_CHANGES_SCRIPT_THRIFT = "get_metastore_changes_thrift.py"
GENERATE_RCLONE_SCRIPT = "generate_rclone_script.py"
GENERATE_PAIMON_SCRIPT = "generate_paimon_statements.py"

# 生成动态输出目录名称：output/yyyyMMddHHmmss
# 注：根据需求采用 yyyyMMddHHmmss 格式
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")
DEFAULT_BASE_DIR = "output"
CURRENT_OUTPUT_DIR = os.path.join(DEFAULT_BASE_DIR, TIMESTAMP)

def check_script_exists(script_name):
    """检查依赖脚本是否存在"""
    if not os.path.exists(script_name):
        print(f"错误：依赖脚本 '{script_name}' 未找到。")
        sys.exit(1)

def run_command(command, step_name):
    """执行外部命令并处理异常"""
    print(f"\n{'='*20}\n步骤: {step_name}\n执行: {' '.join(command)}\n{'='*20}")
    try:
        subprocess.check_call(command)
        print(f"--- 步骤 '{step_name}' 成功完成 ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n!!! 错误：步骤 '{step_name}' 失败，返回码: {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"\n!!! 未知错误: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Hive元数据同步全流程编排：增量查询 -> 数据迁移脚本 -> Paimon同步脚本",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("-c", "--config", default="config.ini", help="配置文件路径 (默认: config.ini)")
    parser.add_argument("-s", "--start-time", required=True, help="查询开始时间 (YYYY-MM-DD HH:MM:SS)")
    
    # 动态定义输出路径
    parser.add_argument("--delta-csv", help="增量结果CSV路径 (默认在当前时间戳目录下)")
    parser.add_argument("--rclone-script", help="生成的rclone脚本路径")
    parser.add_argument("--paimon-script", help="生成的Paimon SQL路径")
    parser.add_argument("--schema-changes", help="结构变更记录路径")

    args = parser.parse_args()

    # 根据配置文件中的 connection_mode 选择增量查询脚本
    config = configparser.ConfigParser()
    config.read(args.config)
    connection_mode = config.get('general', 'connection_mode', fallback='db').lower()
    if connection_mode == 'thrift':
        get_changes_script = GET_CHANGES_SCRIPT_THRIFT
        print(f"连接模式: Thrift (HMS Thrift API)")
    else:
        get_changes_script = GET_CHANGES_SCRIPT_DB
        print(f"连接模式: DB (直连 Metastore 数据库)")

    # 如果未指定具体路径，则默认使用当前时间戳目录
    delta_csv = args.delta_csv or os.path.join(CURRENT_OUTPUT_DIR, "metastore_delta.csv")
    rclone_sh = args.rclone_script or os.path.join(CURRENT_OUTPUT_DIR, "sync_commands.sh")
    paimon_sql = args.paimon_script or os.path.join(CURRENT_OUTPUT_DIR, "paimon_sync.sql")
    schema_txt = args.schema_changes or os.path.join(CURRENT_OUTPUT_DIR, "schema_changes.txt")

    # 1. 环境准备：创建输出目录并检查依赖脚本
    os.makedirs(CURRENT_OUTPUT_DIR, exist_ok=True)
    for s in [get_changes_script, GENERATE_RCLONE_SCRIPT, GENERATE_PAIMON_SCRIPT]:
        check_script_exists(s)

    # 2. 步骤1: 执行增量元数据查询 
    cmd1 = [
        sys.executable, get_changes_script, 
        "-c", args.config, 
        "-s", args.start_time, 
        "-o", delta_csv
    ]
    run_command(cmd1, "1. 查询Hive Metastore增量变更")

    # 3. 步骤2: 生成 rclone 数据同步脚本
    cmd2 = [
        sys.executable, GENERATE_RCLONE_SCRIPT, 
        "-c", args.config, 
        "-i", delta_csv, 
        "--output-script", rclone_sh, 
        "--output-schema-changes", schema_txt
    ]
    run_command(cmd2, "2. 生成rclone数据迁移脚本")

    # 4. 步骤3: 生成 Paimon 元数据同步脚本 
    cmd3 = [
        sys.executable, GENERATE_PAIMON_SCRIPT, 
        "-c", args.config, 
        "-i", delta_csv, 
        "-o", paimon_sql
    ]
    run_command(cmd3, "3. 生成Paimon元数据同步脚本")

    print(f"\n{'*'*30}\n编排任务全部成功！")
    print(f"输出目录: {CURRENT_OUTPUT_DIR}")
    print(f"1. 增量详情: {delta_csv}")
    print(f"2. 数据迁移: {rclone_sh}")
    print(f"3. Paimon同步: {paimon_sql}")
    if os.path.exists(schema_txt):
        print(f"4. 结构变更记录: {schema_txt}")
    print(f"{'*'*30}")

if __name__ == "__main__":
    main()

