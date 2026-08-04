#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import configparser
import csv
import sys
import subprocess
import re
from urllib.parse import urlparse

def read_config(config_path):
    """读取并验证配置文件"""
    config = configparser.ConfigParser()
    if not config.read(config_path):
        print(f"错误：无法读取配置文件 '{config_path}'。")
        sys.exit(1)
    
    if not config.has_section('rclone_target_s3') or not config.has_option('rclone_target_s3', 'bucket'):
        print(f"错误：配置文件中缺少 [rclone_target_s3] 的 bucket 配置。")
        sys.exit(1)
    
    return config

def run_hive_cmd(cmd, config=None):
    """执行 Hive 命令并获取输出。
    
    支持两种模式（通过 config.ini [hive_cli] 段配置）：
    - beeline 模式: 需配置 jdbc_url, username, password
    - hive 模式（默认）: 直接调用 hive -S -e
    """
    try:
        if config and config.has_section('hive_cli'):
            cli_cfg = config['hive_cli']
            mode = cli_cfg.get('mode', 'hive').lower()
            if mode == 'beeline':
                jdbc_url = cli_cfg.get('jdbc_url', '')
                username = cli_cfg.get('username', 'hive')
                password = cli_cfg.get('password', '')
                if not jdbc_url:
                    print("错误：[hive_cli] 配置了 beeline 模式但缺少 jdbc_url")
                    return None
                beeline_cmd = [
                    'beeline', '-u', jdbc_url,
                    '-n', username, '-p', password,
                    '--silent=true', '--showHeader=false',
                    '--outputformat=tsv2', '-e', cmd
                ]
                result = subprocess.check_output(beeline_cmd, stderr=subprocess.PIPE)
            else:
                result = subprocess.check_output(
                    ['hive', '-S', '-e', cmd], stderr=subprocess.PIPE)
        else:
            result = subprocess.check_output(
                ['hive', '-S', '-e', cmd], stderr=subprocess.PIPE)
        return result.decode('utf-8')
    except Exception as e:
        print(f"执行 Hive 命令失败: {cmd}\n错误信息: {e}")
        return None

def clean_hive_ddl(raw_ddl, db_name, new_tbl_name, is_paimon_ext=False, oss_path=None):
    """
    重构 Hive DDL 并转换为 Paimon 语法。
    1. 动态识别源文件格式 (PARQUET/ORC/CSV/JSON)。
    2. 将分区字段合并入主表字段定义。
    3. 修复 PARTITIONED BY 语法为仅包含列名。
    """
    # 1. 识别文件格式
    fmt = 'orc'  # 默认值
    ddl_lower = raw_ddl.lower()
    if 'parquet' in ddl_lower: fmt = 'parquet'
    elif 'json' in ddl_lower: fmt = 'json'
    elif 'csv' in ddl_lower or 'serde2.lazy' in ddl_lower: fmt = 'csv'
    elif 'orc' in ddl_lower: fmt = 'orc'

    # 2. 提取字段和分区信息
    # 移除 Hive 特有的 ROW FORMAT/LOCATION/TBLPROPERTIES 等部分防止干扰
    clean_raw = re.split(r'ROW FORMAT|STORED AS|LOCATION|TBLPROPERTIES', raw_ddl, flags=re.IGNORECASE)[0]
    
    main_cols_def = ""
    part_cols_def = ""
    part_names = []

    # 匹配主表括号中的内容和 PARTITIONED BY 括号中的内容
    if 'PARTITIONED BY' in clean_raw.upper():
        parts = re.split(r'PARTITIONED BY', clean_raw, flags=re.IGNORECASE)
        # 主字段部分
        main_match = re.search(r'\((.*)\)', parts[0], re.DOTALL)
        if main_match:
            main_cols_def = main_match.group(1).strip()
        # 分区字段定义部分
        part_match = re.search(r'\((.*)\)', parts[1], re.DOTALL)
        if part_match:
            part_cols_def = part_match.group(1).strip()
            # 提取分区字段的名称（例如 `year` int -> `year`）
            for col_def in part_cols_def.split(','):
                name_match = re.search(r'[`\w]+', col_def.strip())
                if name_match:
                    part_names.append(name_match.group(0))
    else:
        main_match = re.search(r'\((.*)\)', clean_raw, re.DOTALL)
        if main_match:
            main_cols_def = main_match.group(1).strip()

    # 3. 组装字段：Paimon 要求分区字段必须也在主字段定义中 <sub index="1" url="https://blog.csdn.net/gitblog_01182/article/details/148758542" title="Apache Paimon：从Hive表迁移到Paimon表的完整指南" snippet="本文将详细介绍如何将现有的Hive表迁移到Paimon表。### 迁移前须知在开始迁移前，有几个关键点需要特别注意：* 数据备份  ：迁移过程不是原子操作，如果中途失败可能导致数据丢失，强烈建议先备份原始Hive表数据* 格式支持  ：目前支持迁移Hive中的ORC、Parquet和Avro格式表* 表类型  ：迁移后的Paimon表将是追加表(Append Table)类型* 不可逆性  ：迁移完成后，原Hive表将被删除，无法再通过Hive方式读写### 迁移方式选择Paimon提供了两种主要迁移方式：* 单表迁移  ：适用于只需要迁移特定表的情况* 整库迁移  ：适用于需要将整个Hive数据库迁移到Paimon的场景### 单表迁移实践#### 使用Flink SQL迁移-- 首先创建Paimon Catalog，连接到Hive MetastoreCREATE CATALOG PAIMON WITH (   'type'='paimon',   'metastore' = 'hive',   'uri' = 'thrift://localhost:9083',   'warehouse'='/path/to/warehouse/');-- 使用Paimon CatalogUSE CATALOG PAIMON;-- 执行迁移命令CALL sys.migrate_table(    connector =&gt; 'hive',    source_table =&gt; 'default.hivetable',    options =&gt; 'file.format=orc');**参数说明** ：* source_table：指定要迁移的Hive表，格式为* 数据库名.表名* options：指定文件格式，支持orc/parquet/avro* 可选参数target_table：可指定目标Paimon表名* 可选参数delete_origin：设为false可保留原Hive表#### 使用Flink Action迁移&lt;FLINK_HOME&gt;/flink run paimon-flink-action-*.jar \migrate_table \--warehouse /path/to/warehouse \--catalog_conf uri=thrift://localhost:9083 \--catalog_conf metastore=hive \--source_type hive \--table default.hive_table### 整库迁移实践#### 使用Flink SQL迁移整个数据库-- 创建Catalog同上CREATE CATALOG PAIMON WITH (...);USE CATALOG PAIMON;-- 迁移整个数据库CALL sys.migrate_database(    connector =&gt; 'hive',    source_database =&gt; 'default',    options =&gt; 'file.format=orc');#### 使用Flink Action迁移整个数据库&lt;FLINK_HOME&gt;/flink run paimon-flink-action-*.jar \migrate_database \--warehouse /path/to/warehouse \--catalog_conf uri=thrift://localhost:9083 \--catalog_conf metastore=hive \--source_type hive \--database default### 迁移后的验证迁移完成后，建议进行以下验证步骤：* 数据完整性检查  ：对比迁移前后的数据行数* Schema验证  ：确保字段类型和约束正确迁移* 查询测试  ：执行一些典型查询验证性能### 常见问题处理* 迁移中断  ：如果迁移过程意外中断，可能需要从备份恢复* 格式不匹配  ：确保指定的文件格式与Hive表实际格式一致* 权限问题  ：确保有足够的权限访问Hive Metastore和目标存储位置### 最佳实践建议* 分批迁移  ：对于大型数据库，建议分批迁移表而非一次性全库迁移* 业务低峰期  ：选择业务低峰期执行迁移，减少对生产环境的影响* 监控资源  ：迁移过程可能消耗大量资源，建议监控集群状态### 总结将Hive表迁移到Apache Paimon可以带来更好的流批一体处理能力和增量更新特性。通过本文介绍的两种迁移方式，用户可以根据实际需求选择最适合的方案。记住始终先备份数据，并在测试环境验证后再在生产环境执行迁移。"></sub>
    combined_cols = main_cols_def
    if part_cols_def:
        combined_cols += ",\n  " + part_cols_def

    # 4. 构建 DDL
    ddl = f"CREATE TABLE IF NOT EXISTS {db_name}.{new_tbl_name} (\n  {combined_cols}\n)"
    
    if part_names:
        ddl += f"\nPARTITIONED BY ({', '.join(part_names)})"
    
    ddl += "\nUSING paimon"

    # 5. 注入 TBLPROPERTIES
    props = []
    if is_paimon_ext and oss_path:
        props.append(f"'path' = '{oss_path}'")
        props.append("'type' = 'format-table'") # 指定为 format-table 模式 <sub index="1" url="https://blog.csdn.net/gitblog_01182/article/details/148758542" title="Apache Paimon：从Hive表迁移到Paimon表的完整指南" snippet="本文将详细介绍如何将现有的Hive表迁移到Paimon表。### 迁移前须知在开始迁移前，有几个关键点需要特别注意：* 数据备份  ：迁移过程不是原子操作，如果中途失败可能导致数据丢失，强烈建议先备份原始Hive表数据* 格式支持  ：目前支持迁移Hive中的ORC、Parquet和Avro格式表* 表类型  ：迁移后的Paimon表将是追加表(Append Table)类型* 不可逆性  ：迁移完成后，原Hive表将被删除，无法再通过Hive方式读写### 迁移方式选择Paimon提供了两种主要迁移方式：* 单表迁移  ：适用于只需要迁移特定表的情况* 整库迁移  ：适用于需要将整个Hive数据库迁移到Paimon的场景### 单表迁移实践#### 使用Flink SQL迁移-- 首先创建Paimon Catalog，连接到Hive MetastoreCREATE CATALOG PAIMON WITH (   'type'='paimon',   'metastore' = 'hive',   'uri' = 'thrift://localhost:9083',   'warehouse'='/path/to/warehouse/');-- 使用Paimon CatalogUSE CATALOG PAIMON;-- 执行迁移命令CALL sys.migrate_table(    connector =&gt; 'hive',    source_table =&gt; 'default.hivetable',    options =&gt; 'file.format=orc');**参数说明** ：* source_table：指定要迁移的Hive表，格式为* 数据库名.表名* options：指定文件格式，支持orc/parquet/avro* 可选参数target_table：可指定目标Paimon表名* 可选参数delete_origin：设为false可保留原Hive表#### 使用Flink Action迁移&lt;FLINK_HOME&gt;/flink run paimon-flink-action-*.jar \migrate_table \--warehouse /path/to/warehouse \--catalog_conf uri=thrift://localhost:9083 \--catalog_conf metastore=hive \--source_type hive \--table default.hive_table### 整库迁移实践#### 使用Flink SQL迁移整个数据库-- 创建Catalog同上CREATE CATALOG PAIMON WITH (...);USE CATALOG PAIMON;-- 迁移整个数据库CALL sys.migrate_database(    connector =&gt; 'hive',    source_database =&gt; 'default',    options =&gt; 'file.format=orc');#### 使用Flink Action迁移整个数据库&lt;FLINK_HOME&gt;/flink run paimon-flink-action-*.jar \migrate_database \--warehouse /path/to/warehouse \--catalog_conf uri=thrift://localhost:9083 \--catalog_conf metastore=hive \--source_type hive \--database default### 迁移后的验证迁移完成后，建议进行以下验证步骤：* 数据完整性检查  ：对比迁移前后的数据行数* Schema验证  ：确保字段类型和约束正确迁移* 查询测试  ：执行一些典型查询验证性能### 常见问题处理* 迁移中断  ：如果迁移过程意外中断，可能需要从备份恢复* 格式不匹配  ：确保指定的文件格式与Hive表实际格式一致* 权限问题  ：确保有足够的权限访问Hive Metastore和目标存储位置### 最佳实践建议* 分批迁移  ：对于大型数据库，建议分批迁移表而非一次性全库迁移* 业务低峰期  ：选择业务低峰期执行迁移，减少对生产环境的影响* 监控资源  ：迁移过程可能消耗大量资源，建议监控集群状态### 总结将Hive表迁移到Apache Paimon可以带来更好的流批一体处理能力和增量更新特性。通过本文介绍的两种迁移方式，用户可以根据实际需求选择最适合的方案。记住始终先备份数据，并在测试环境验证后再在生产环境执行迁移。"></sub>
        props.append(f"'file.format' = '{fmt}'")
    
    if props:
        ddl += "\nTBLPROPERTIES (\n  " + ",\n  ".join(props) + "\n)"

    # 6. 清理多余空行
    lines = [line.rstrip() for line in ddl.splitlines() if line.strip()]
    return "\n".join(lines) + ";"

def get_partition_clause(keys_str, values_str, mode='dml'):
    """处理多级分区逻辑"""
    if not keys_str or not values_str:
        return ""
    keys = [k.strip() for k in keys_str.split(',')]
    vals = values_str.split('/')
    parts = [f"{k}='{v}'" for k, v in zip(keys, vals)]
    return ", ".join(parts) if mode == 'dml' else " AND ".join(parts)

def generate_statements(row, bucket, config=None):
    db, tbl = row['db_name'], row['table_name']
    full_tbl = f"{db}.{tbl}"
    change_type = row['type']
    is_part = row['is_partitioned'] == '1'
    parsed_url = urlparse(row['location'])
    oss_path = f"oss://{bucket}{parsed_url.path}"

    sqls = []
    if change_type == 'TABLE_CREATE':
        print(f"  --> 正在处理表: {full_tbl}")
        raw_ddl = run_hive_cmd(f"SHOW CREATE TABLE {full_tbl}", config)
        if not raw_ddl: return []
        
        # A. 生成 OSS 外表
        ext_tbl_name = f"{tbl}_lhm_ext"
        ext_ddl = clean_hive_ddl(raw_ddl, db, ext_tbl_name, is_paimon_ext=True, oss_path=oss_path)
        sqls.append(f"-- 1. 创建 OSS 外表\n{ext_ddl}")

        # B. 生成 Paimon 内表
        int_ddl = clean_hive_ddl(raw_ddl, db, tbl, is_paimon_ext=False)
        sqls.append(f"-- 2. 创建 Paimon 内表\n{int_ddl}")

        # C. 初始化同步语句
        if is_part:
            p_keys = row['partition_keys']
            dml = f"INSERT OVERWRITE TABLE {full_tbl} PARTITION ({p_keys}) SELECT * FROM {db}.{ext_tbl_name};"
        else:
            dml = f"INSERT OVERWRITE TABLE {full_tbl} SELECT * FROM {db}.{ext_tbl_name};"
        sqls.append(f"-- 3. 初始化数据同步\n{dml}")
    elif change_type == 'DATA_MODIFIED':
        dml = f"INSERT OVERWRITE TABLE {full_tbl} SELECT * FROM {full_tbl}_lhm_ext;"
        sqls.append(f"-- 数据变更同步: {full_tbl}\n{dml}")
    elif change_type in ['PARTITION_CREATE', 'PARTITION_MODIFIED']:
        p_dml = get_partition_clause(row['partition_keys'], row['partition_values'], 'dml')
        p_where = get_partition_clause(row['partition_keys'], row['partition_values'], 'where')
        dml = f"INSERT OVERWRITE TABLE {full_tbl} PARTITION ({p_dml}) SELECT * FROM {full_tbl}_lhm_ext WHERE {p_where};"
        sqls.append(f"-- 分区变更同步: {full_tbl} ({row['partition_values']})\n{dml}")

    return sqls

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.ini")
    parser.add_argument("-i", "--input", default="metastore_delta.csv")
    parser.add_argument("-o", "--output", default="paimon_sync.sql")
    args = parser.parse_args()

    config = read_config(args.config)
    bucket = config.get('rclone_target_s3', 'bucket')
    all_statements = []

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['type'] == 'TABLE_MODIFIED': continue
                sqls = generate_statements(row, bucket, config)
                if sqls: all_statements.extend(sqls)

        if all_statements:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write("-- Paimon Sync Script\n\n" + "\n\n".join(all_statements) + "\n")
            print(f"成功！结果已保存至: {args.output}")
    except Exception as e:
        print(f"处理失败: {e}")

if __name__ == "__main__":
    main()

