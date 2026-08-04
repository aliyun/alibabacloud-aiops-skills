#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hive 数据表深度探查 (Thrift 版)

通过 Hive Metastore Thrift Service (端口 9083) 获取所有表的元数据、存储大小和 DDL。
输出格式与 hive_dive.sh 完全一致，可被下游工具直接消费。
"""

import argparse
import configparser
import os
import subprocess
import sys
from datetime import datetime

# 将脚本所在目录加入 sys.path 以便导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thrift_client import ThriftHMSConnection
from ddl_builder import build_ddl


def format_bytes(num_bytes):
    """将字节数转换为人类可读格式（与 hive_dive.sh 中的 format_bytes 一致）"""
    if num_bytes is None or num_bytes < 0:
        return "N/A"
    if num_bytes == 0:
        return "0 B"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024 ** 3:
        return f"{num_bytes / 1024 ** 2:.2f} MB"
    elif num_bytes < 1024 ** 4:
        return f"{num_bytes / 1024 ** 3:.2f} GB"
    else:
        return f"{num_bytes / 1024 ** 4:.2f} TB"


def get_size_from_params(table, client):
    """从表参数获取存储大小（totalSize），分区表尝试汇总"""
    params = table.parameters or {}
    total_size = params.get('totalSize')
    if total_size and total_size != '0':
        try:
            return int(total_size)
        except (ValueError, TypeError):
            pass

    # 分区表：汇总各分区的 totalSize
    partition_keys = table.partitionKeys or []
    if partition_keys:
        try:
            partitions = client.get_partitions(table.dbName, table.tableName, -1)
            total = 0
            found_any = False
            for p in partitions:
                p_params = p.parameters or {}
                p_size = p_params.get('totalSize')
                if p_size:
                    try:
                        total += int(p_size)
                        found_any = True
                    except (ValueError, TypeError):
                        pass
            if found_any:
                return total
        except Exception:
            pass

    return None


def get_size_from_hadoop(location, error_log_path):
    """通过 hadoop fs -du -s 获取存储大小"""
    if not location:
        return None
    try:
        result = subprocess.run(
            ['hadoop', 'fs', '-du', '-s', location],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            size_str = result.stdout.strip().split()[0]
            return int(size_str)
        else:
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"hadoop fs -du -s {location} 失败: {result.stderr}\n")
    except FileNotFoundError:
        with open(error_log_path, 'a', encoding='utf-8') as f:
            f.write("hadoop 命令未找到，请确认 HADOOP_HOME 已配置\n")
    except subprocess.TimeoutExpired:
        with open(error_log_path, 'a', encoding='utf-8') as f:
            f.write(f"hadoop fs -du -s {location} 超时\n")
    except Exception as e:
        with open(error_log_path, 'a', encoding='utf-8') as f:
            f.write(f"hadoop fs -du -s {location} 异常: {e}\n")
    return None


def run_full_exploration(thrift_config, target_dbs=None, size_source='params', output_dir=None):
    """
    核心全量探查逻辑，可被 hive_explore.py 直接调用。

    参数:
        thrift_config: Thrift 配置字典或 ConfigParser section
        target_dbs: 数据库列表，None 表示全部
        size_source: 表大小获取方式 (params/hadoop/skip)
        output_dir: 输出目录，None 则自动生成

    返回:
        str: 输出目录路径
    """
    today = datetime.now().strftime('%Y%m%d')
    if output_dir is None:
        suffix = 'batch' if target_dbs else 'all_dbs'
        output_dir = f"hive_explore_{suffix}_{today}"

    ddl_subdir = os.path.join(output_dir, 'ddl_files')
    csv_path = os.path.join(output_dir, 'summary_report.csv')
    error_log = os.path.join(output_dir, 'error.log')

    os.makedirs(ddl_subdir, exist_ok=True)

    # 初始化错误日志
    with open(error_log, 'w', encoding='utf-8') as f:
        pass

    print("====== Hive 数据表深度探查（Thrift 模式）开始 ======")
    print(f"所有输出文件将保存在目录: {output_dir}")

    with open(csv_path, 'w', encoding='utf-8') as csv_file:
        csv_file.write("db_name,tbl_name,tbl_location,total_size_bytes,total_size_human,ddl_file_path\n")

        with ThriftHMSConnection(thrift_config) as client:
            # 获取数据库列表
            if target_dbs is None:
                target_dbs = client.get_all_databases()
                print(f"未指定数据库，将探查所有 Hive 数据库（共 {len(target_dbs)} 个）...")
            else:
                print(f"目标数据库: {' '.join(target_dbs)}")

            for db_name in target_dbs:
                try:
                    table_names = client.get_all_tables(db_name)
                except Exception as e:
                    print(f"  -> 获取数据库 {db_name} 的表列表失败: {e}")
                    with open(error_log, 'a', encoding='utf-8') as f:
                        f.write(f"get_all_tables({db_name}) 失败: {e}\n")
                    continue

                print(f"\n数据库: {db_name} (共 {len(table_names)} 张表)")

                for tbl_name in table_names:
                    try:
                        table = client.get_table(db_name, tbl_name)
                    except Exception as e:
                        print(f"  -> 获取表 {db_name}.{tbl_name} 元数据失败: {e}")
                        with open(error_log, 'a', encoding='utf-8') as f:
                            f.write(f"get_table({db_name}, {tbl_name}) 失败: {e}\n")
                        continue

                    # 过滤视图
                    tbl_type = getattr(table, 'tableType', '') or ''
                    if tbl_type in ('VIRTUAL_VIEW', 'MATERIALIZED_VIEW'):
                        continue

                    print(f"-------------------------------------------")
                    print(f"正在处理: {db_name}.{tbl_name}")

                    # 获取 location
                    location = ''
                    if table.sd:
                        location = table.sd.location or ''

                    # 获取存储大小
                    total_size_bytes = None
                    if size_source == 'params':
                        total_size_bytes = get_size_from_params(table, client)
                    elif size_source == 'hadoop':
                        total_size_bytes = get_size_from_hadoop(location, error_log)
                    # size_source == 'skip' 时不获取

                    if total_size_bytes is not None:
                        human_size = format_bytes(total_size_bytes)
                        size_bytes_str = str(total_size_bytes)
                        print(f"  -> 大小: {human_size} ({total_size_bytes} Bytes)")
                    else:
                        human_size = "N/A"
                        size_bytes_str = "N/A"
                        if size_source != 'skip':
                            print(f"  -> 大小: N/A (统计信息不可用)")

                    # 生成 DDL
                    ddl_file_path = os.path.join(ddl_subdir, f"{db_name}.{tbl_name}.sql")
                    print(f"  -> 导出 DDL 到: {ddl_file_path}")
                    try:
                        ddl = build_ddl(table)
                        with open(ddl_file_path, 'w', encoding='utf-8') as f:
                            f.write(ddl)
                    except Exception as e:
                        print(f"  -> 错误: 生成 DDL 失败: {e}")
                        with open(ddl_file_path, 'w', encoding='utf-8') as f:
                            f.write(f"-- FAILED TO GET DDL for {db_name}.{tbl_name}\n")
                        with open(error_log, 'a', encoding='utf-8') as f:
                            f.write(f"DDL 生成失败 {db_name}.{tbl_name}: {e}\n")

                    # 写入 CSV
                    csv_file.write(f'{db_name},{tbl_name},"{location}",{size_bytes_str},{human_size},{ddl_file_path}\n')

    print("===========================================")
    print("所有表处理完毕！")
    print(f"汇总报告请查看: {csv_path}")
    print(f"所有建表语句 DDL 文件位于: {ddl_subdir}")
    print(f"处理过程中遇到的任何异常，请查看日志文件: {error_log}")
    print("====== 探查结束 ======")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Hive 数据表深度探查 (Thrift 版)")
    parser.add_argument("-c", "--config", default="config.ini", help="配置文件路径")
    parser.add_argument("databases", nargs='*', help="要探查的数据库列表（不指定则探查全部）")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    if 'thrift' not in config:
        print("错误：配置文件中缺少 [thrift] 段。")
        sys.exit(1)

    thrift_config = config['thrift']
    size_source = thrift_config.get('size_source', 'params').lower()
    target_dbs = args.databases if args.databases else None

    run_full_exploration(thrift_config, target_dbs, size_source)


if __name__ == "__main__":
    main()
