#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import configparser
import csv
import sys
from datetime import datetime

def get_db_connection(config):
    """根据配置建立数据库连接"""
    db_type = config.get('db_type', 'mysql').lower()
    host = config.get('host')
    port = config.getint('port')
    user = config.get('user')
    password = config.get('password')
    database = config.get('database')

    try:
        if db_type == 'mysql':
            import pymysql
            conn = pymysql.connect(
                host=host, port=port, user=user, password=password,
                database=database, cursorclass=pymysql.cursors.DictCursor
            )
            return conn, db_type
        elif db_type == 'postgres':
            import psycopg2
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, dbname=database
            )
            return conn, db_type
        else:
            print(f"错误：不支持的数据库类型 '{db_type}'。")
            sys.exit(1)
    except Exception as e:
        print(f"数据库连接失败: {e}")
        sys.exit(1)

def execute_query(cursor, query, params):
    """执行SQL查询并返回结果"""
    try:
        cursor.execute(query, params)
        results = cursor.fetchall()
        if results and not isinstance(results[0], dict):
             return [dict(row) for row in results]
        return results
    except Exception as e:
        print(f"查询失败: {e}")
        return []

def get_changes(conn, db_type, start_timestamp):
    """查询增量变更，并应用 TABLE_CREATE 优先过滤逻辑"""
    changes = []  
    newly_created_tables = set()  # (db_name, table_name)
    modified_tables = set()       # (db_name, table_name)
    created_partitions = set()    # (db_name, table_name, partition_name)
    cursor = conn.cursor()

    try:
        # SQL 片段准备
        if db_type == 'mysql':
            cast_to_int = "CAST(param_value AS SIGNED)"
            pk_subquery = "(SELECT GROUP_CONCAT(PKEY_NAME ORDER BY INTEGER_IDX SEPARATOR ',') FROM PARTITION_KEYS pk WHERE pk.TBL_ID = t.TBL_ID)"
            is_part_sql = "(CASE WHEN EXISTS (SELECT 1 FROM PARTITION_KEYS pk WHERE pk.TBL_ID = t.TBL_ID) THEN 1 ELSE 0 END)"
        else: # postgres
            cast_to_int = "CAST(param_value AS BIGINT)"
            pk_subquery = "(SELECT STRING_AGG(PKEY_NAME, ',' ORDER BY INTEGER_IDX) FROM PARTITION_KEYS pk WHERE pk.TBL_ID = t.TBL_ID)"
            is_part_sql = "(CASE WHEN EXISTS (SELECT 1 FROM PARTITION_KEYS pk WHERE pk.TBL_ID = t.TBL_ID) THEN 1 ELSE 0 END)"

        common_cols = f"d.NAME AS db_name, t.TBL_NAME AS table_name, {is_part_sql} AS is_partitioned, {pk_subquery} AS partition_keys"

        # 1. TABLE_CREATE: 记录新创建的表
        query_table_create = f"""
            SELECT 'TABLE_CREATE' AS type, {common_cols},
                   NULL AS partition_name, s.LOCATION AS location, t.CREATE_TIME AS change_unix_ts
            FROM TBLS t JOIN DBS d ON t.DB_ID = d.DB_ID JOIN SDS s ON t.SD_ID = s.SD_ID
            WHERE t.CREATE_TIME > %s
        """
        table_creates = execute_query(cursor, query_table_create, (start_timestamp,))
        for r in table_creates:
            newly_created_tables.add((r['db_name'], r['table_name']))
            changes.append(r)

        # 2. TABLE_MODIFIED: 过滤掉属于新表的变更
        query_table_modified = f"""
            SELECT 'TABLE_MODIFIED' AS type, {common_cols},
                   NULL AS partition_name, s.LOCATION AS location, {cast_to_int} AS change_unix_ts
            FROM TABLE_PARAMS tp JOIN TBLS t ON tp.TBL_ID = t.TBL_ID
            JOIN DBS d ON t.DB_ID = d.DB_ID JOIN SDS s ON t.SD_ID = s.SD_ID
            WHERE tp.PARAM_KEY = 'last_modified_time' AND {cast_to_int} > %s
        """
        for r in execute_query(cursor, query_table_modified, (start_timestamp,)):
            if (r['db_name'], r['table_name']) not in newly_created_tables:
                modified_tables.add((r['db_name'], r['table_name']))
                changes.append(r)

        # 3. DATA_MODIFIED (非分区表): 过滤掉新表和已在 TABLE_MODIFIED 中的表
        query_data_modified = f"""
            SELECT 'DATA_MODIFIED' AS type, {common_cols},
                   NULL AS partition_name, s.LOCATION AS location, {cast_to_int} AS change_unix_ts
            FROM TABLE_PARAMS tp JOIN TBLS t ON tp.TBL_ID = t.TBL_ID
            JOIN DBS d ON t.DB_ID = d.DB_ID JOIN SDS s ON t.SD_ID = s.SD_ID
            LEFT JOIN PARTITION_KEYS pk ON t.TBL_ID = pk.TBL_ID
            WHERE tp.PARAM_KEY = 'transient_lastDdlTime' AND pk.TBL_ID IS NULL AND {cast_to_int} > %s
        """
        for r in execute_query(cursor, query_data_modified, (start_timestamp,)):
            db_tbl = (r['db_name'], r['table_name'])
            if db_tbl not in newly_created_tables and db_tbl not in modified_tables:
                changes.append(r)

        # 4. PARTITION_CREATE: 过滤掉属于新表的分区
        query_part_create = f"""
            SELECT 'PARTITION_CREATE' AS type, {common_cols},
                   p.PART_NAME AS partition_name, s.LOCATION AS location, p.CREATE_TIME AS change_unix_ts
            FROM PARTITIONS p JOIN TBLS t ON p.TBL_ID = t.TBL_ID
            JOIN DBS d ON t.DB_ID = d.DB_ID JOIN SDS s ON p.SD_ID = s.SD_ID
            WHERE p.CREATE_TIME > %s
        """
        for r in execute_query(cursor, query_part_create, (start_timestamp,)):
            if (r['db_name'], r['table_name']) not in newly_created_tables:
                created_partitions.add((r['db_name'], r['table_name'], r['partition_name']))
                changes.append(r)

        # 5. PARTITION_MODIFIED: 过滤新表分区和新创建的分区
        query_part_modified = f"""
            SELECT 'PARTITION_MODIFIED' AS type, {common_cols},
                   p.PART_NAME AS partition_name, s.LOCATION AS location, {cast_to_int} AS change_unix_ts
            FROM PARTITION_PARAMS pp JOIN PARTITIONS p ON pp.PART_ID = p.PART_ID
            JOIN TBLS t ON p.TBL_ID = t.TBL_ID JOIN DBS d ON t.DB_ID = d.DB_ID
            JOIN SDS s ON p.SD_ID = s.SD_ID
            WHERE pp.PARAM_KEY = 'transient_lastDdlTime' AND {cast_to_int} > %s
        """
        for r in execute_query(cursor, query_part_modified, (start_timestamp,)):
            db_tbl = (r['db_name'], r['table_name'])
            p_key = (r['db_name'], r['table_name'], r['partition_name'])
            if db_tbl not in newly_created_tables and p_key not in created_partitions:
                changes.append(r)
    finally:
        cursor.close()
    return changes

def clean_partition_name(raw_name):
    if not raw_name: return ""
    return "/".join([p.split('=')[1] if '=' in p else p for p in raw_name.split('/')])

def main():
    parser = argparse.ArgumentParser(description="Hive Metastore 增量变更提取工具")
    parser.add_argument("-c", "--config", default="config.ini", help="配置文件路径")
    parser.add_argument("-s", "--start-time", required=True, help="开始时间 YYYY-MM-DD HH:MM:SS")
    parser.add_argument("-o", "--output", default="metastore_delta.csv", help="输出CSV路径")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    # 支持 config.ini 中使用 ${ENV_VAR} 引用环境变量（如 password=${HIVE_METASTORE_PWD}）
    try:
        from config_manager import expand_env_vars
        expand_env_vars(config)
    except ImportError:
        pass
    conn, db_type = get_db_connection(config['metastore_db'])

    try:
        start_ts = int(datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S').timestamp())
        records = get_changes(conn, db_type, start_ts)
        
        if records:
            records.sort(key=lambda x: x['change_unix_ts'])
            with open(args.output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['type', 'db_name', 'table_name', 'is_partitioned', 'partition_keys', 'partition_values', 'location', 'change_time'])
                for r in records:
                    change_time = datetime.fromtimestamp(int(r['change_unix_ts'])).strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow([r['type'], r['db_name'], r['table_name'], r['is_partitioned'], 
                                     r.get('partition_keys') or '', clean_partition_name(r.get('partition_name')), 
                                     r.get('location') or '', change_time])
            print(f"成功导出 {len(records)} 条变更记录至 {args.output}")
        else:
            print("指定时间内无变更。")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
