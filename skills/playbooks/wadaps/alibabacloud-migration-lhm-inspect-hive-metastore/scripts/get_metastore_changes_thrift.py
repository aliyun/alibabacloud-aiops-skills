#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hive Metastore 增量变更提取工具 (Thrift 版)

通过 Hive Metastore Thrift Service 遍历表和分区，
检测指定时间节点之后的变更，输出格式与 get_metastore_changes.py 完全一致。
"""

import argparse
import configparser
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thrift_client import ThriftHMSConnection


def clean_partition_name(raw_name):
    """清理分区名称，去除键名仅保留值（与 get_metastore_changes.py 一致）"""
    if not raw_name:
        return ""
    return "/".join([p.split('=')[1] if '=' in p else p for p in raw_name.split('/')])


def reconstruct_part_name(partition_keys, partition_values):
    """
    从分区键列表和分区值列表重建 PART_NAME 格式。

    例如: keys=['dt','region'], values=['2026-01-12','us-west']
          → 'dt=2026-01-12/region=us-west'
    """
    if not partition_keys or not partition_values:
        return ""
    parts = []
    for i, pk in enumerate(partition_keys):
        key_name = pk.name if hasattr(pk, 'name') else str(pk)
        val = partition_values[i] if i < len(partition_values) else ''
        parts.append(f"{key_name}={val}")
    return "/".join(parts)


def get_changes(client, start_ts, target_dbs=None):
    """
    通过 Thrift API 遍历表和分区，检测增量变更。

    实现与 get_metastore_changes.py 相同的五阶段去重逻辑：
    TABLE_CREATE > TABLE_MODIFIED > DATA_MODIFIED > PARTITION_CREATE > PARTITION_MODIFIED
    """
    changes = []
    newly_created_tables = set()   # (db_name, table_name)
    modified_tables = set()        # (db_name, table_name)
    created_partitions = set()     # (db_name, table_name, partition_name)

    # 获取数据库列表
    if target_dbs:
        all_dbs = target_dbs
    else:
        all_dbs = client.get_all_databases()

    total_dbs = len(all_dbs)
    for db_idx, db_name in enumerate(all_dbs, 1):
        try:
            table_names = client.get_all_tables(db_name)
        except Exception as e:
            print(f"  警告: 获取数据库 {db_name} 表列表失败: {e}")
            continue

        print(f"  [{db_idx}/{total_dbs}] 数据库: {db_name} ({len(table_names)} 张表)")

        for tbl_name in table_names:
            try:
                table = client.get_table(db_name, tbl_name)
            except Exception as e:
                print(f"    警告: 获取表 {db_name}.{tbl_name} 失败: {e}")
                continue

            # 过滤视图
            tbl_type = getattr(table, 'tableType', '') or ''
            if tbl_type in ('VIRTUAL_VIEW', 'MATERIALIZED_VIEW'):
                continue

            params = table.parameters or {}
            partition_keys = table.partitionKeys or []
            is_partitioned = 1 if partition_keys else 0
            pk_names = ','.join([pk.name for pk in partition_keys]) if partition_keys else ''
            location = table.sd.location if table.sd else ''

            # 基础记录模板
            base_record = {
                'db_name': db_name,
                'table_name': tbl_name,
                'is_partitioned': is_partitioned,
                'partition_keys': pk_names,
            }

            # === 阶段1: TABLE_CREATE ===
            create_time = getattr(table, 'createTime', 0) or 0
            if create_time > start_ts:
                newly_created_tables.add((db_name, tbl_name))
                changes.append({
                    **base_record,
                    'type': 'TABLE_CREATE',
                    'partition_name': None,
                    'location': location,
                    'change_unix_ts': create_time,
                })
                continue  # 新表不再检查其他变更类型

            db_tbl = (db_name, tbl_name)

            # === 阶段2: TABLE_MODIFIED ===
            last_modified = params.get('last_modified_time')
            if last_modified:
                try:
                    lm_ts = int(last_modified)
                    if lm_ts > start_ts and db_tbl not in newly_created_tables:
                        modified_tables.add(db_tbl)
                        changes.append({
                            **base_record,
                            'type': 'TABLE_MODIFIED',
                            'partition_name': None,
                            'location': location,
                            'change_unix_ts': lm_ts,
                        })
                except (ValueError, TypeError):
                    pass

            # === 阶段3: DATA_MODIFIED (仅非分区表) ===
            if not is_partitioned:
                transient_ddl = params.get('transient_lastDdlTime')
                if transient_ddl:
                    try:
                        ddl_ts = int(transient_ddl)
                        if (ddl_ts > start_ts
                                and db_tbl not in newly_created_tables
                                and db_tbl not in modified_tables):
                            changes.append({
                                **base_record,
                                'type': 'DATA_MODIFIED',
                                'partition_name': None,
                                'location': location,
                                'change_unix_ts': ddl_ts,
                            })
                    except (ValueError, TypeError):
                        pass

            # === 阶段4 & 5: 分区变更 (仅分区表且非新建表) ===
            if is_partitioned and db_tbl not in newly_created_tables:
                try:
                    partitions = client.get_partitions(db_name, tbl_name, -1)
                except Exception as e:
                    print(f"    警告: 获取表 {db_name}.{tbl_name} 分区失败: {e}")
                    continue

                for p in partitions:
                    part_name = reconstruct_part_name(partition_keys, p.values)
                    p_create_time = getattr(p, 'createTime', 0) or 0
                    p_params = p.parameters or {}
                    p_location = p.sd.location if p.sd else ''

                    # === 阶段4: PARTITION_CREATE ===
                    if p_create_time > start_ts:
                        created_partitions.add((db_name, tbl_name, part_name))
                        changes.append({
                            **base_record,
                            'type': 'PARTITION_CREATE',
                            'partition_name': part_name,
                            'location': p_location,
                            'change_unix_ts': p_create_time,
                        })
                        continue

                    # === 阶段5: PARTITION_MODIFIED ===
                    p_ddl_time = p_params.get('transient_lastDdlTime')
                    if p_ddl_time:
                        try:
                            p_ddl_ts = int(p_ddl_time)
                            p_key = (db_name, tbl_name, part_name)
                            if (p_ddl_ts > start_ts
                                    and p_key not in created_partitions):
                                changes.append({
                                    **base_record,
                                    'type': 'PARTITION_MODIFIED',
                                    'partition_name': part_name,
                                    'location': p_location,
                                    'change_unix_ts': p_ddl_ts,
                                })
                        except (ValueError, TypeError):
                            pass

    return changes


def main():
    parser = argparse.ArgumentParser(description="Hive Metastore 增量变更提取工具 (Thrift 版)")
    parser.add_argument("-c", "--config", default="config.ini", help="配置文件路径")
    parser.add_argument("-s", "--start-time", required=True, help="开始时间 YYYY-MM-DD HH:MM:SS")
    parser.add_argument("-o", "--output", default="metastore_delta.csv", help="输出CSV路径")
    parser.add_argument("--databases", nargs='*', help="限制扫描的数据库列表（不指定则扫描全部）")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    # 支持 config.ini 中使用 ${ENV_VAR} 引用环境变量
    try:
        from config_manager import expand_env_vars
        expand_env_vars(config)
    except ImportError:
        pass

    if 'thrift' not in config:
        print("错误：配置文件中缺少 [thrift] 段。")
        sys.exit(1)

    start_ts = int(datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S').timestamp())
    print(f"查询起始时间: {args.start_time} (Unix: {start_ts})")

    with ThriftHMSConnection(config['thrift']) as client:
        records = get_changes(client, start_ts, target_dbs=args.databases)

    if records:
        records.sort(key=lambda x: x['change_unix_ts'])
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['type', 'db_name', 'table_name', 'is_partitioned',
                             'partition_keys', 'partition_values', 'location', 'change_time'])
            for r in records:
                change_time = datetime.fromtimestamp(
                    int(r['change_unix_ts'])
                ).strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([
                    r['type'],
                    r['db_name'],
                    r['table_name'],
                    r['is_partitioned'],
                    r.get('partition_keys') or '',
                    clean_partition_name(r.get('partition_name')),
                    r.get('location') or '',
                    change_time,
                ])
        print(f"成功导出 {len(records)} 条变更记录至 {args.output}")
    else:
        print("指定时间内无变更。")


if __name__ == "__main__":
    main()
