#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hive-to-Paimon 存量迁移 - 公共模块
提供 DDL 解析、配置读取、Spark Thrift 执行器等基础能力
"""

import configparser
import csv
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# TableMeta 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ColumnDef:
    """列定义"""
    name: str
    type: str
    comment: str = ""


@dataclass
class TableMeta:
    """表元数据"""
    db_name: str
    table_name: str
    columns: List[ColumnDef] = field(default_factory=list)
    partition_columns: List[ColumnDef] = field(default_factory=list)
    comment: str = ""
    storage_format: str = "orc"  # orc|parquet|json|csv|text
    location: str = ""
    raw_ddl: str = ""
    error: str = ""

    @property
    def full_name(self):
        return f"{self.db_name}.{self.table_name}"

    @property
    def is_partitioned(self):
        return len(self.partition_columns) > 0

    @property
    def partition_keys(self):
        return ",".join(c.name for c in self.partition_columns)

    @property
    def all_columns(self):
        """主字段 + 分区字段合并"""
        return self.columns + self.partition_columns

    @property
    def column_count(self):
        return len(self.all_columns)

    def columns_to_json(self):
        """将完整列定义序列化为 JSON 字符串"""
        cols = [{"name": c.name, "type": c.type, "comment": c.comment}
                for c in self.all_columns]
        return json.dumps(cols, ensure_ascii=False)

    @staticmethod
    def columns_from_json(json_str):
        """从 JSON 字符串还原列定义列表"""
        return [ColumnDef(**c) for c in json.loads(json_str)]


# ---------------------------------------------------------------------------
# DDL 解析器
# ---------------------------------------------------------------------------

def _strip_backticks(name: str) -> str:
    """去除反引号"""
    return name.strip().strip('`').strip()


def _detect_storage_format(ddl_text: str) -> str:
    """从 DDL 文本识别存储格式"""
    lower = ddl_text.lower()

    # TextFile 必须同时匹配 TextInputFormat 和 LazySimpleSerDe
    if 'textinputformat' in lower and ('lazysimple' in lower or 'serde2.lazy' in lower):
        return 'text'

    if 'parquet' in lower:
        return 'parquet'
    if 'orc' in lower:
        return 'orc'
    if 'json' in lower:
        return 'json'
    if 'csv' in lower or 'serde2.lazy' in lower or 'opencsvserde' in lower:
        return 'csv'

    return 'orc'  # 默认


def _parse_columns_block(block: str) -> List[ColumnDef]:
    """
    解析字段定义块，支持多行 COMMENT 和嵌套括号（如 decimal(12,2)）。
    输入示例:
      `month_ids` string COMMENT '月份',
      `bill_amount` decimal(12,2) COMMENT '金额'
    """
    columns = []
    if not block or not block.strip():
        return columns

    # 按逗号分割，但要跳过括号内的逗号和引号内的逗号
    parts = []
    depth = 0
    in_quote = False
    current = []
    for ch in block:
        if ch == "'" and depth == 0:
            in_quote = not in_quote
            current.append(ch)
        elif ch == '(' and not in_quote:
            depth += 1
            current.append(ch)
        elif ch == ')' and not in_quote:
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0 and not in_quote:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current).strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 匹配: `name` type [COMMENT 'xxx']
        # 或:    name type [COMMENT 'xxx']
        m = re.match(
            r'`?(\w+)`?\s+'
            r'([\w()., ]+?)'
            r'(?:\s+COMMENT\s+\'((?:[^\'\\]|\\.|\'\')*)\')?\s*$',
            part, re.IGNORECASE | re.DOTALL
        )
        if m:
            col_name = m.group(1).strip()
            col_type = m.group(2).strip()
            col_comment = (m.group(3) or '').replace("''", "'")
            columns.append(ColumnDef(name=col_name, type=col_type, comment=col_comment))
        else:
            # 尝试更宽松的匹配: `name` type
            m2 = re.match(r'`?(\w+)`?\s+([\w()., ]+)', part, re.IGNORECASE)
            if m2:
                columns.append(ColumnDef(name=m2.group(1).strip(),
                                         type=m2.group(2).strip()))

    return columns


def parse_hive_ddl(raw_ddl: str) -> TableMeta:
    """
    解析 Hive DDL 文本为结构化 TableMeta。
    支持 CREATE TABLE / CREATE EXTERNAL TABLE 格式。
    """
    meta = TableMeta(db_name="", table_name="", raw_ddl=raw_ddl)

    try:
        # 1. 提取 db.table 名称
        name_match = re.search(
            r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'
            r'`?(\w+)`?\.`?(\w+)`?\s*\(',
            raw_ddl, re.IGNORECASE
        )
        if not name_match:
            # 尝试只有表名没有库名的格式
            name_match = re.search(
                r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'
                r'`?(\w+)`?\s*\(',
                raw_ddl, re.IGNORECASE
            )
            if name_match:
                meta.table_name = _strip_backticks(name_match.group(1))
            else:
                meta.error = "无法解析表名"
                return meta
        else:
            meta.db_name = _strip_backticks(name_match.group(1))
            meta.table_name = _strip_backticks(name_match.group(2))

        # 2. 识别存储格式（在截断前从完整 DDL 中识别）
        meta.storage_format = _detect_storage_format(raw_ddl)

        # 3. 提取 LOCATION
        loc_match = re.search(r"LOCATION\s*\n?\s*'([^']+)'", raw_ddl, re.IGNORECASE)
        if loc_match:
            meta.location = loc_match.group(1)

        # 4. 提取表级 COMMENT（在 PARTITIONED BY 或 ROW FORMAT 之前的独立 COMMENT 行）
        # 先尝试从截断后的区域提取
        comment_match = re.search(
            r"^\s*COMMENT\s+'((?:[^'\\]|\\.|'')*)'",
            raw_ddl, re.IGNORECASE | re.MULTILINE
        )
        if comment_match:
            meta.comment = comment_match.group(1).replace("''", "'")

        # 5. 截断 ROW FORMAT 及之后的内容，得到干净的结构区
        clean_ddl = re.split(
            r'\nROW\s+FORMAT|\nSTORED\s+AS|\nLOCATION|\nTBLPROPERTIES',
            raw_ddl, maxsplit=1, flags=re.IGNORECASE
        )[0]

        # 6. 分离主字段和分区字段
        if re.search(r'PARTITIONED\s+BY', clean_ddl, re.IGNORECASE):
            parts = re.split(r'PARTITIONED\s+BY', clean_ddl, maxsplit=1, flags=re.IGNORECASE)
            main_part = parts[0]
            part_part = parts[1] if len(parts) > 1 else ""

            # 提取主字段：从 CREATE TABLE ... ( 到最后的 )
            main_match = re.search(r'CREATE\s+(?:EXTERNAL\s+)?TABLE[^(]*\((.*)\)',
                                   main_part, re.DOTALL | re.IGNORECASE)
            if main_match:
                # 需要找到正确的闭合括号
                content_after_open = main_part[main_part.index('(') + 1:]
                # 从后往前找最后一个 ) —— 考虑 COMMENT 行可能在 ) 之后
                depth = 0
                end_idx = -1
                for i in range(len(content_after_open) - 1, -1, -1):
                    if content_after_open[i] == ')':
                        if depth == 0:
                            end_idx = i
                            break
                        depth -= 1
                    elif content_after_open[i] == '(':
                        depth += 1
                if end_idx >= 0:
                    main_cols_text = content_after_open[:end_idx]
                else:
                    main_cols_text = main_match.group(1)
                meta.columns = _parse_columns_block(main_cols_text)

            # 提取分区字段
            part_match = re.search(r'\(\s*(.*?)\s*\)', part_part, re.DOTALL)
            if part_match:
                meta.partition_columns = _parse_columns_block(part_match.group(1))
        else:
            # 非分区表：提取所有字段
            open_idx = clean_ddl.find('(')
            if open_idx >= 0:
                content = clean_ddl[open_idx + 1:]
                # 找最外层闭合 )
                depth = 0
                end_idx = -1
                for i in range(len(content) - 1, -1, -1):
                    if content[i] == ')':
                        if depth == 0:
                            end_idx = i
                            break
                        depth -= 1
                    elif content[i] == '(':
                        depth += 1
                if end_idx >= 0:
                    meta.columns = _parse_columns_block(content[:end_idx])

    except Exception as e:
        meta.error = f"DDL 解析异常: {e}"

    return meta


# ---------------------------------------------------------------------------
# 表清单解析（两种输入来源）
# ---------------------------------------------------------------------------

def load_tables_from_explore_dir(explore_dir: str,
                                 filter_dbs: Optional[List[str]] = None,
                                 filter_tables: Optional[List[str]] = None) -> List[TableMeta]:
    """
    从 migration-lhm-inspect-hive-metastore 全量探查输出目录加载表元数据。
    explore_dir 应包含 summary_report.csv 和 ddl_files/ 子目录。
    """
    tables = []
    summary_csv = os.path.join(explore_dir, 'summary_report.csv')
    ddl_dir = os.path.join(explore_dir, 'ddl_files')

    if not os.path.exists(summary_csv):
        print(f"错误：找不到 summary_report.csv: {summary_csv}")
        sys.exit(1)
    if not os.path.isdir(ddl_dir):
        print(f"错误：找不到 ddl_files 目录: {ddl_dir}")
        sys.exit(1)

    with open(summary_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            db_name = row.get('db_name', '').strip()
            tbl_name = row.get('tbl_name', '').strip()
            tbl_location = row.get('tbl_location', '').strip().strip('"')

            # 过滤
            if filter_dbs and db_name not in filter_dbs:
                continue
            if filter_tables and f"{db_name}.{tbl_name}" not in filter_tables:
                continue

            # 读取 DDL 文件
            ddl_file = os.path.join(ddl_dir, f"{db_name}.{tbl_name}.sql")
            if not os.path.exists(ddl_file):
                tables.append(TableMeta(
                    db_name=db_name, table_name=tbl_name,
                    location=tbl_location,
                    error=f"DDL 文件不存在: {ddl_file}"
                ))
                continue

            with open(ddl_file, 'r', encoding='utf-8') as df:
                raw_ddl = df.read()

            meta = parse_hive_ddl(raw_ddl)
            # summary_report.csv 的 location 可能更准确
            if tbl_location and not meta.location:
                meta.location = tbl_location
            # 确保 db_name 正确（DDL 中可能缺失）
            if not meta.db_name:
                meta.db_name = db_name
            if not meta.table_name:
                meta.table_name = tbl_name

            tables.append(meta)

    print(f"从探查目录加载了 {len(tables)} 张表")
    return tables


def load_tables_from_metastore(config, databases=None, tables_list=None) -> List[TableMeta]:
    """
    从 Hive Metastore DB 直接查询表清单并获取 DDL。
    需要 [metastore_db] 配置和可用的 hive/beeline CLI。
    """
    import subprocess

    db_cfg = config['metastore_db']
    db_type = db_cfg.get('db_type', 'mysql').lower()
    host = db_cfg['host']
    port = int(db_cfg['port'])
    user = db_cfg['user']
    password = db_cfg['password']
    database = db_cfg['database']

    # 构建查询
    where_clauses = ["(tbl.TBL_TYPE = 'MANAGED_TABLE' OR tbl.TBL_TYPE = 'EXTERNAL_TABLE')"]
    if databases:
        db_list = ",".join(f"'{d}'" for d in databases)
        where_clauses.append(f"db.NAME IN ({db_list})")
    if tables_list:
        # tables_list 格式: ["db.table", ...]
        conditions = []
        for t in tables_list:
            parts = t.split('.')
            if len(parts) == 2:
                conditions.append(f"(db.NAME = '{parts[0]}' AND tbl.TBL_NAME = '{parts[1]}')")
        if conditions:
            where_clauses.append("(" + " OR ".join(conditions) + ")")

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT db.NAME, tbl.TBL_NAME, sds.LOCATION
        FROM TBLS tbl
        JOIN DBS db ON tbl.DB_ID = db.DB_ID
        JOIN SDS sds ON tbl.SD_ID = sds.SD_ID
        WHERE {where_sql}
        ORDER BY db.NAME, tbl.TBL_NAME
    """

    try:
        if db_type == 'mysql':
            import pymysql
            conn = pymysql.connect(host=host, port=port, user=user, password=password,
                                   database=database, cursorclass=pymysql.cursors.DictCursor)
        elif db_type == 'postgres':
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(host=host, port=port, user=user, password=password,
                                    dbname=database)
        else:
            print(f"错误：不支持的数据库类型 '{db_type}'")
            sys.exit(1)
    except Exception as e:
        print(f"Metastore 数据库连接失败: {e}")
        sys.exit(1)

    results = []
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        if not isinstance(rows[0], dict) if rows else True:
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(zip(col_names, row)) for row in rows] if rows else []
        cursor.close()
    finally:
        conn.close()

    print(f"从 Metastore 查询到 {len(rows)} 张表，正在获取 DDL...")

    table_metas = []
    for row in rows:
        db_name = row.get('NAME', '')
        tbl_name = row.get('TBL_NAME', '')
        location = row.get('LOCATION', '')

        # 通过 hive CLI 获取 DDL
        try:
            result = subprocess.run(
                ['hive', '-S', '-e', f'SHOW CREATE TABLE `{db_name}`.`{tbl_name}`'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                meta = parse_hive_ddl(result.stdout)
                if not meta.location and location:
                    meta.location = location
                if not meta.db_name:
                    meta.db_name = db_name
                if not meta.table_name:
                    meta.table_name = tbl_name
                table_metas.append(meta)
            else:
                table_metas.append(TableMeta(
                    db_name=db_name, table_name=tbl_name, location=location,
                    error=f"hive CLI 获取 DDL 失败: {result.stderr[:200]}"
                ))
        except Exception as e:
            table_metas.append(TableMeta(
                db_name=db_name, table_name=tbl_name, location=location,
                error=f"获取 DDL 异常: {e}"
            ))

    print(f"成功解析 {sum(1 for t in table_metas if not t.error)} 张表的 DDL")
    return table_metas


# ---------------------------------------------------------------------------
# Manifest CSV 读写
# ---------------------------------------------------------------------------

MANIFEST_FIELDS = [
    'db_name', 'table_name', 'storage_format', 'is_partitioned',
    'partition_keys', 'hdfs_location', 'column_count', 'columns_json', 'error'
]


def write_manifest(tables: List[TableMeta], output_path: str):
    """将表元数据列表写入 manifest CSV"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for t in tables:
            writer.writerow({
                'db_name': t.db_name,
                'table_name': t.table_name,
                'storage_format': t.storage_format,
                'is_partitioned': '1' if t.is_partitioned else '0',
                'partition_keys': t.partition_keys,
                'hdfs_location': t.location,
                'column_count': t.column_count,
                'columns_json': t.columns_to_json(),
                'error': t.error,
            })
    print(f"Manifest 已写入: {output_path} ({len(tables)} 张表)")


def read_manifest(manifest_path: str) -> List[TableMeta]:
    """从 manifest CSV 读取表元数据列表"""
    tables = []
    with open(manifest_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cols_all = TableMeta.columns_from_json(row.get('columns_json', '[]'))
            partition_keys = [k.strip() for k in row.get('partition_keys', '').split(',') if k.strip()]

            # 分离主字段和分区字段
            main_cols = []
            part_cols = []
            for c in cols_all:
                if c.name in partition_keys:
                    part_cols.append(c)
                else:
                    main_cols.append(c)

            meta = TableMeta(
                db_name=row['db_name'],
                table_name=row['table_name'],
                columns=main_cols,
                partition_columns=part_cols,
                storage_format=row.get('storage_format', 'orc'),
                location=row.get('hdfs_location', ''),
                error=row.get('error', ''),
            )
            tables.append(meta)
    print(f"从 Manifest 加载了 {len(tables)} 张表")
    return tables


# ---------------------------------------------------------------------------
# 线程安全工具（ResultWriter / safe_print）
# ---------------------------------------------------------------------------

print_lock = threading.Lock()


def safe_print(msg, log_f=None):
    """线程安全的打印，同时写入日志文件"""
    with print_lock:
        print(msg)
        if log_f:
            log_f.write(msg + '\n')
            log_f.flush()


class ResultWriter:
    """线程安全的增量 CSV 写入器，每完成一条就追加写入"""

    def __init__(self, path, header):
        self._path = path
        self._lock = threading.Lock()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

    def append(self, row):
        with self._lock:
            with open(self._path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)


# ---------------------------------------------------------------------------
# 配置读取
# ---------------------------------------------------------------------------

def read_config(config_path: str, required_sections: Optional[dict] = None) -> configparser.ConfigParser:
    """
    读取配置文件并验证必需的 section 和 key。
    required_sections: {"section_name": ["key1", "key2"], ...}

    配置值支持 ${ENV_VAR} 语法，导入时自动展开环境变量
    （未定义的变量保持原样，方便后续用 validate_config_values 捕获）。
    """
    config = configparser.ConfigParser()
    if not config.read(config_path):
        print(f"错误：无法读取配置文件 '{config_path}'")
        sys.exit(1)

    # 环境变量插值：将 ${VAR} / $VAR 替换为 os.environ 中的值
    for section in config.sections():
        for key, val in config.items(section):
            if val and '$' in val:
                config.set(section, key, os.path.expandvars(val))

    if required_sections:
        for section, keys in required_sections.items():
            if not config.has_section(section):
                print(f"错误：配置文件中缺少 [{section}]")
                sys.exit(1)
            for key in keys:
                if not config.has_option(section, key):
                    print(f"错误：[{section}] 中缺少 '{key}'")
                    sys.exit(1)

    return config


# 占位符检测正则
_PLACEHOLDER_PATTERNS = [
    re.compile(r'^\$your_', re.IGNORECASE),
    re.compile(r'^\$YOUR_'),
    re.compile(r'^YOUR_'),
    re.compile(r'^your_'),
    re.compile(r'^<.+>$'),
]


def validate_config_values(config, sections):
    """
    检查指定 section 的配置值是否仍为占位符。
    sections: {"section_name": ["key1", "key2"], ...}
    返回警告信息列表（空列表 = 全部通过）。
    """
    warnings = []
    for section, keys in sections.items():
        if not config.has_section(section):
            continue
        for key in keys:
            if not config.has_option(section, key):
                continue
            val = config.get(section, key).strip()
            if not val:
                warnings.append(f"[{section}] {key} = '' (值为空)")
                continue
            for pat in _PLACEHOLDER_PATTERNS:
                if pat.search(val):
                    warnings.append(f"[{section}] {key} = '{val}' (疑似占位符)")
                    break
    return warnings


# ---------------------------------------------------------------------------
# Spark Thrift Executor
# ---------------------------------------------------------------------------

class SparkThriftExecutor:
    """通过 pyhive 连接 Spark Thrift Server 执行 SQL"""

    def __init__(self, config: configparser.ConfigParser):
        """从 config 的 [spark_thrift] section 初始化连接"""
        from pyhive import hive

        section = 'spark_thrift'
        self.host = config.get(section, 'host')
        self.port = config.getint(section, 'port')
        self.username = config.get(section, 'username', fallback=None)
        self.password = config.get(section, 'password', fallback=None)
        self.database = config.get(section, 'database', fallback='default')
        self.auth = config.get(section, 'auth', fallback='NONE')
        self.scheme = config.get(section, 'scheme', fallback='https')

        self.connection = None
        self.cursor = None

        print(f"正在连接 Spark Thrift Server: {self.scheme}://{self.host}:{self.port}")
        try:
            self.connection = hive.connect(
                host=self.host,
                port=self.port,
                scheme=self.scheme,
                username=self.username,
                password=self.password,
                database=self.database,
                auth=self.auth,
                configuration={'spark.sql.timestampType': 'TIMESTAMP_LTZ'},
            )
            self.cursor = self.connection.cursor()
            print("连接成功!")

            # 设置 TIMESTAMP 类型
            try:
                self.cursor.execute("SET spark.sql.timestampType=TIMESTAMP_LTZ")
                print("已设置 spark.sql.timestampType=TIMESTAMP_LTZ")
            except Exception as e:
                print(f"警告: 设置 timestampType 失败: {e}")

        except Exception as e:
            print(f"连接失败: {e}")
            raise

    def execute_sql(self, sql: str, log_file=None) -> Tuple[bool, str]:
        """
        执行单条 SQL。返回 (success, error_msg)。
        log_file: 可选的文件对象，同时写入执行日志。
        """
        sql = sql.strip()
        if not sql or sql.startswith('--'):
            return True, ""

        def _log(msg):
            print(msg)
            if log_file:
                log_file.write(msg + '\n')
                log_file.flush()

        try:
            start = time.time()
            self.cursor.execute(sql)
            elapsed = time.time() - start
            _log(f"  [OK] ({elapsed:.1f}s) {sql[:100]}{'...' if len(sql) > 100 else ''}")
            return True, ""
        except Exception as e:
            err = str(e)
            _log(f"  [FAIL] {sql[:100]}{'...' if len(sql) > 100 else ''}")
            _log(f"         错误: {err[:200]}")
            return False, err

    def execute_sql_file(self, filepath: str, log_dir: Optional[str] = None,
                         continue_on_error: bool = True,
                         log_file=None) -> Tuple[int, int, int, list]:
        """
        执行 SQL 文件，按分号分割逐条执行。
        返回 (total, success, failed, error_list)
        log_file: 可选的文件对象，同时写入执行日志。
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        statements = self._split_statements(content)
        total = len(statements)
        success = 0
        failed = 0
        error_list = []

        def _log(msg, end='\n'):
            print(msg, end=end)
            if log_file:
                log_file.write(msg + end)
                log_file.flush()

        _log(f"\n执行 SQL 文件: {filepath} ({total} 条语句)")

        # 准备日志
        error_log_path = None
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(filepath))[0]
            error_log_path = os.path.join(log_dir, f"{base}_errors.log")

        for i, sql in enumerate(statements, 1):
            _log(f"[{i}/{total}] ", end='')
            ok, err = self.execute_sql(sql, log_file=log_file)
            if ok:
                success += 1
            else:
                failed += 1
                error_list.append({"index": i, "sql": sql, "error": err})

                if not continue_on_error:
                    _log("遇到错误，停止执行")
                    break

        # 写错误日志
        if error_list and error_log_path:
            self._write_error_log(error_log_path, filepath, error_list)
            _log(f"错误日志: {error_log_path}")

        _log(f"执行完成: 总计 {total}, 成功 {success}, 失败 {failed}")
        return total, success, failed, error_list

    def _split_statements(self, content: str) -> List[str]:
        """按分号分割 SQL，忽略注释，引号感知"""
        # 移除多行注释
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        statements = []
        current_chars = []
        in_quote = False

        for line in content.split('\n'):
            stripped = line.strip()
            if not in_quote and stripped.startswith('--'):
                continue

            i = 0
            while i < len(line):
                ch = line[i]
                if ch == "'":
                    if in_quote and i + 1 < len(line) and line[i + 1] == "'":
                        current_chars.append("''")
                        i += 2
                        continue
                    in_quote = not in_quote
                    current_chars.append(ch)
                elif ch == ';' and not in_quote:
                    stmt = ''.join(current_chars).strip()
                    if stmt:
                        statements.append(stmt)
                    current_chars = []
                else:
                    current_chars.append(ch)
                i += 1

            current_chars.append('\n')

        if current_chars:
            stmt = ''.join(current_chars).strip()
            if stmt:
                statements.append(stmt)

        return statements

    def _write_error_log(self, log_path: str, source_file: str, errors: list):
        """写入错误日志"""
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"SQL 执行错误日志\n")
            f.write(f"源文件: {source_file}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"错误数: {len(errors)}\n")
            f.write("=" * 60 + "\n\n")
            for i, err in enumerate(errors, 1):
                f.write(f"--- 错误 #{i} (第 {err['index']} 条) ---\n")
                f.write(f"错误信息: {err['error']}\n")
                f.write(f"SQL:\n{err['sql']}\n\n")

    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("Spark 连接已关闭")

    def test_connection(self):
        """执行 SELECT 1 测试连接是否可用，返回 (bool, str)"""
        try:
            self.cursor.execute("SELECT 1")
            return True, ""
        except Exception as e:
            return False, str(e)

    @classmethod
    def quick_test(cls, config):
        """创建临时连接执行 SELECT 1 后关闭，用于预检查，返回 (bool, str)"""
        try:
            executor = cls(config)
            ok, err = executor.test_connection()
            executor.close()
            return ok, err
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# SQL 解析工具
# ---------------------------------------------------------------------------

def extract_table_name_from_sql(sql: str) -> str:
    """从 DDL/DML 语句中提取表名（db.table 格式）"""
    # CREATE TABLE IF NOT EXISTS db.table(
    m = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)', sql, re.IGNORECASE)
    if m:
        return m.group(1).replace('`', '')
    # INSERT OVERWRITE [TABLE] db.table
    m = re.search(r'INSERT\s+OVERWRITE\s+(?:TABLE\s+)?([^\s(]+)', sql, re.IGNORECASE)
    if m:
        return m.group(1).replace('`', '')
    return 'unknown'


# 错误分类规则: (pattern, category, suggestion)
_ERROR_RULES = [
    (re.compile(r'Database .* not found|NoSuchDatabaseException|database .* does not exist',
                re.IGNORECASE),
     'DATABASE_NOT_FOUND',
     '使用 --auto-create-db 自动建库，或先执行 CREATE DATABASE IF NOT EXISTS'),
    (re.compile(r'Table .* already exists|AlreadyExistsException|TableExistsException',
                re.IGNORECASE),
     'TABLE_EXISTS',
     '使用 --force 强制 DROP + CREATE 重建'),
    (re.compile(r'Connection refused|TTransportException|Could not connect|Broken pipe',
                re.IGNORECASE),
     'CONNECTION_ERROR',
     '检查 Spark Thrift Server 是否运行，确认 [spark_thrift] host/port 配置'),
    (re.compile(r'Authentication|GSS|SASL|401|403|Unauthorized', re.IGNORECASE),
     'AUTH_ERROR',
     '检查 [spark_thrift] username/password/auth 配置'),
    (re.compile(r'AnalysisException', re.IGNORECASE),
     'SQL_ERROR',
     '检查 SQL 语法、表名、列名是否正确'),
    (re.compile(r'OutOfMemoryError|Java heap space|GC overhead', re.IGNORECASE),
     'OOM_ERROR',
     '增大 Spark executor/driver 内存，或减少并行度'),
    (re.compile(r'TimeoutException|timed? ?out', re.IGNORECASE),
     'TIMEOUT',
     '检查网络连接，或增大超时时间'),
]


def classify_error(error_msg):
    """对 Spark/Hive 异常进行分类，返回 (category, suggestion)。"""
    for pattern, category, suggestion in _ERROR_RULES:
        if pattern.search(error_msg):
            return category, suggestion
    return 'UNKNOWN', '查看完整错误日志获取更多信息'


def split_sql_file(filepath: str) -> List[str]:
    """
    读取 SQL 文件并按分号分割为独立语句。
    引号感知：COMMENT 内的分号（如 '状态(1:有效\\;2:无效)'）不会触发拆分。
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除块注释
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    statements = []
    current_chars = []
    in_quote = False

    for line in content.split('\n'):
        stripped = line.strip()
        # 非引号状态下跳过纯注释行
        if not in_quote and stripped.startswith('--'):
            continue

        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "'":
                # 处理 SQL 转义的单引号 ''
                if in_quote and i + 1 < len(line) and line[i + 1] == "'":
                    current_chars.append("''")
                    i += 2
                    continue
                in_quote = not in_quote
                current_chars.append(ch)
            elif ch == ';' and not in_quote:
                # 引号外的分号 = 语句结束符
                stmt = ''.join(current_chars).strip()
                if stmt:
                    statements.append(stmt)
                current_chars = []
            else:
                current_chars.append(ch)
            i += 1

        current_chars.append('\n')

    # 处理没有尾部分号的剩余内容
    if current_chars:
        stmt = ''.join(current_chars).strip()
        if stmt:
            statements.append(stmt)

    return statements


# ---------------------------------------------------------------------------
# 数据校验
# ---------------------------------------------------------------------------

def verify_row_count(executor: 'SparkThriftExecutor',
                     source_table: str,
                     target_table: str) -> Tuple[bool, int, int, str]:
    """
    比较源表(外表)和目标表(内表)行数。
    返回 (match, source_count, target_count, error)。
    """
    def _count(table):
        try:
            executor.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row = executor.cursor.fetchone()
            return row[0] if row else -1, ""
        except Exception as e:
            return -1, str(e)

    src_cnt, src_err = _count(source_table)
    if src_err:
        return False, -1, -1, f"源表 COUNT 失败: {src_err}"

    tgt_cnt, tgt_err = _count(target_table)
    if tgt_err:
        return False, src_cnt, -1, f"目标表 COUNT 失败: {tgt_err}"

    return src_cnt == tgt_cnt, src_cnt, tgt_cnt, ""


# ---------------------------------------------------------------------------
# 进度追踪器
# ---------------------------------------------------------------------------

class ProgressTracker:
    """线程安全的进度追踪器，支持 ETA 计算"""

    def __init__(self, total: int, label: str = ""):
        self.total = total
        self.label = label
        self.completed = 0
        self._lock = threading.Lock()
        self.start_time = time.time()

    def tick(self, item_name: str = "") -> str:
        """递增完成数，返回格式化进度字符串"""
        with self._lock:
            self.completed += 1
            current = self.completed

        elapsed = time.time() - self.start_time
        if current > 0 and current < self.total:
            avg = elapsed / current
            remaining = avg * (self.total - current)
            eta = self._format_duration(remaining)
            eta_str = f", 预计剩余 ~{eta}"
        else:
            eta_str = ""

        elapsed_str = self._format_duration(elapsed)
        name_str = f" {item_name}" if item_name else ""
        return f"[{current}/{self.total}]{name_str} (已用 {elapsed_str}{eta_str})"

    def summary(self) -> str:
        """返回总耗时摘要"""
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_duration(elapsed)
        avg = elapsed / self.completed if self.completed > 0 else 0
        return (f"总计 {self.completed}/{self.total}, "
                f"耗时 {elapsed_str}, "
                f"平均 {avg:.1f}s/项")

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化秒数为可读字符串"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m{seconds % 60:.0f}s"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h{m}m"


# ---------------------------------------------------------------------------
# 迁移报告
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """单步骤执行结果"""
    step_num: int
    step_name: str
    status: str = 'skipped'   # success / failed / skipped
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    duration: float = 0.0
    error_details: List[dict] = field(default_factory=list)


@dataclass
class MigrationReport:
    """迁移全流程报告"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    config_path: str = ""
    input_source: str = ""
    output_dir: str = ""
    direct_read: bool = False
    steps: List[StepResult] = field(default_factory=list)
    verify_results: List[dict] = field(default_factory=list)


def write_migration_report(report: MigrationReport, output_dir: str) -> str:
    """
    写入人类可读的迁移报告到 output_dir/migration_report.txt。
    返回报告文件路径。
    """
    report_path = os.path.join(output_dir, 'migration_report.txt')
    if not report.end_time:
        report.end_time = datetime.now()

    total_duration = (report.end_time - report.start_time).total_seconds()

    lines = []
    lines.append("=" * 60)
    lines.append("Hive-to-Paimon 存量迁移报告")
    lines.append("=" * 60)
    lines.append(f"执行时间: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} — "
                 f"{report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"总耗时:   {total_duration:.1f}s ({total_duration / 60:.1f}m)")
    lines.append(f"输入来源: {report.input_source}")
    lines.append(f"配置文件: {report.config_path}")
    lines.append(f"输出目录: {report.output_dir}")
    if report.direct_read:
        lines.append(f"直读模式: 是")
    lines.append("")

    lines.append("-" * 60)
    lines.append("步骤汇总")
    lines.append("-" * 60)
    for sr in report.steps:
        count_info = ""
        if sr.total > 0:
            count_info = f"  {sr.success_count}/{sr.total} 成功"
            if sr.failed_count > 0:
                count_info += f", {sr.failed_count} 失败"
        lines.append(f"  Step {sr.step_num}: {sr.step_name:<20s} {sr.status:<6s} "
                     f"({sr.duration:.1f}s){count_info}")
    lines.append("")

    # 失败明细
    has_failures = any(sr.error_details for sr in report.steps)
    if has_failures:
        lines.append("-" * 60)
        lines.append("失败明细")
        lines.append("-" * 60)
        for sr in report.steps:
            for err in sr.error_details:
                lines.append(f"  [Step {sr.step_num}] {err.get('table', 'unknown')}: "
                             f"{err.get('error', '')[:150]}")
        lines.append("")

    # 校验结果
    if report.verify_results:
        lines.append("-" * 60)
        lines.append("数据校验结果")
        lines.append("-" * 60)
        match_count = sum(1 for v in report.verify_results if v.get('match'))
        mismatch_count = sum(1 for v in report.verify_results if not v.get('match'))
        lines.append(f"  匹配: {match_count}, 不匹配: {mismatch_count}")
        for v in report.verify_results:
            if not v.get('match'):
                lines.append(f"  ! {v.get('table', '?')}: "
                             f"源={v.get('source_count', '?')} "
                             f"目标={v.get('target_count', '?')}")
        lines.append("")

    lines.append("=" * 60)

    content = "\n".join(lines) + "\n"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return report_path


# ---------------------------------------------------------------------------
# rclone 安装检测
# ---------------------------------------------------------------------------

def ensure_rclone_installed():
    """
    检查 rclone 是否已安装，未安装则尝试自动安装。
    支持 yum (CentOS/RHEL)、apt (Debian/Ubuntu)、官方安装脚本。
    """
    import shutil
    import subprocess as _sp
    import platform

    if shutil.which('rclone'):
        try:
            ver = _sp.run(['rclone', 'version'], capture_output=True, text=True, timeout=10)
            first_line = ver.stdout.strip().split('\n')[0] if ver.stdout else 'unknown'
            print(f"rclone 已安装: {first_line}")
        except Exception:
            print("rclone 已安装")
        return True

    print("rclone 未安装，尝试自动安装...")

    system = platform.system().lower()
    if system != 'linux':
        print(f"错误: 自动安装仅支持 Linux，当前系统: {system}")
        print("请手动安装 rclone: https://rclone.org/install/")
        return False

    # 尝试方案 1: yum (CentOS/RHEL)
    if shutil.which('yum'):
        print("尝试通过 yum 安装 rclone...")
        result = _sp.run(['yum', 'install', '-y', 'rclone'],
                         capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and shutil.which('rclone'):
            print("rclone 通过 yum 安装成功")
            return True
        print(f"yum 安装失败 (可能需要 epel 源): {result.stderr[:200]}")

        # 尝试先安装 epel-release 再重试
        _sp.run(['yum', 'install', '-y', 'epel-release'],
                capture_output=True, text=True, timeout=120)
        result = _sp.run(['yum', 'install', '-y', 'rclone'],
                         capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and shutil.which('rclone'):
            print("rclone 通过 yum (epel) 安装成功")
            return True

    # 尝试方案 2: apt (Debian/Ubuntu)
    if shutil.which('apt-get'):
        print("尝试通过 apt 安装 rclone...")
        _sp.run(['apt-get', 'update', '-y'], capture_output=True, text=True, timeout=120)
        result = _sp.run(['apt-get', 'install', '-y', 'rclone'],
                         capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and shutil.which('rclone'):
            print("rclone 通过 apt 安装成功")
            return True
        print(f"apt 安装失败: {result.stderr[:200]}")

    # 尝试方案 3: 官方安装脚本
    if shutil.which('curl'):
        print("尝试通过官方脚本安装 rclone...")
        result = _sp.run(
            'curl -s https://rclone.org/install.sh | bash',
            shell=True, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0 and shutil.which('rclone'):
            print("rclone 通过官方脚本安装成功")
            return True
        print(f"官方脚本安装失败: {result.stderr[:200]}")

    print("错误: rclone 自动安装失败，请手动安装:")
    print("  CentOS/RHEL: yum install -y epel-release && yum install -y rclone")
    print("  Debian/Ubuntu: apt-get install -y rclone")
    print("  通用: curl https://rclone.org/install.sh | bash")
    return False


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def hdfs_path_to_oss_path(hdfs_location: str, bucket: str,
                         target_path: str = '') -> str:
    """
    将 HDFS location 转换为 OSS 路径。
    target_path 为空时保持与 HDFS 完全一致；
    指定时替换为 target_path + 表级相对路径（db.db/table 部分）。
    """
    parsed = urlparse(hdfs_location)
    path = parsed.path  # /user/hive/warehouse/db.db/table
    if target_path:
        target_path = target_path.strip('/')
        # 从 HDFS 路径中提取 db.db/table 部分（最后两段）
        parts = path.rstrip('/').split('/')
        if len(parts) >= 2:
            relative = '/'.join(parts[-2:])  # db.db/table
        else:
            relative = path.lstrip('/')
        return f"oss://{bucket}/{target_path}/{relative}"
    return f"oss://{bucket}{path}"


def get_oss_relative_path(hdfs_location: str, target_path: str = '') -> str:
    """
    从 HDFS location 提取用于 rclone 目标的路径部分。
    target_path 为空时返回完整 HDFS 路径；
    指定时返回 target_path + 表级相对路径。
    """
    parsed = urlparse(hdfs_location)
    path = parsed.path
    if target_path:
        target_path = target_path.strip('/')
        parts = path.rstrip('/').split('/')
        if len(parts) >= 2:
            relative = '/'.join(parts[-2:])
        else:
            relative = path.lstrip('/')
        return f"/{target_path}/{relative}"
    return path


def create_output_dir(base_dir: Optional[str] = None) -> str:
    """创建带时间戳的输出目录"""
    if base_dir:
        output_dir = base_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = os.path.join("output", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)
    return output_dir


def add_rclone_override_args(parser):
    """为 argparse 添加 rclone 参数覆盖选项组，供 step4 和 incremental_migrate 共用"""
    group = parser.add_argument_group('rclone 参数覆盖',
                                      '通过 CLI 参数覆盖 config.ini 中的 rclone 配置')
    group.add_argument('--src-namenode', help='HDFS NameNode 地址 (host:port)')
    group.add_argument('--src-username', help='HDFS 用户名')
    group.add_argument('--tgt-provider', help='S3 提供商 (Alibaba/AWS/Minio)')
    group.add_argument('--tgt-endpoint', help='OSS/S3 endpoint')
    group.add_argument('--tgt-ak', help='Access Key ID')
    group.add_argument('--tgt-sk', help='Secret Access Key')
    group.add_argument('--tgt-bucket', help='目标 bucket')
    group.add_argument('--tgt-path', help='目标端根路径 (如 /data/hive)，不指定则保持 HDFS 原始路径')
    group.add_argument('--bwlimit', help='带宽限制 (如 50M, 08:00,off 23:00,30M)')
    group.add_argument('--transfers', type=int, help='rclone 并行传输数')
    group.add_argument('--checkers', type=int, help='rclone 并行检查数')


def apply_rclone_overrides(config: configparser.ConfigParser, args) -> configparser.ConfigParser:
    """
    将 CLI 覆盖参数应用到 config 对象上。
    直接修改并返回 config 对象。
    """
    # 源端 HDFS 配置
    if getattr(args, 'src_namenode', None):
        config.set('rclone_source_hdfs', 'namenode', args.src_namenode)
    if getattr(args, 'src_username', None):
        config.set('rclone_source_hdfs', 'username', args.src_username)

    # 目标端 S3 配置
    if getattr(args, 'tgt_provider', None):
        config.set('rclone_target_s3', 'provider', args.tgt_provider)
    if getattr(args, 'tgt_endpoint', None):
        config.set('rclone_target_s3', 'endpoint', args.tgt_endpoint)
    if getattr(args, 'tgt_ak', None):
        config.set('rclone_target_s3', 'access_key_id', args.tgt_ak)
    if getattr(args, 'tgt_sk', None):
        config.set('rclone_target_s3', 'secret_access_key', args.tgt_sk)
    if getattr(args, 'tgt_bucket', None):
        config.set('rclone_target_s3', 'bucket', args.tgt_bucket)
    if getattr(args, 'tgt_path', None):
        if not config.has_section('rclone_target_s3'):
            config.add_section('rclone_target_s3')
        config.set('rclone_target_s3', 'target_path', args.tgt_path)

    # rclone 选项
    if getattr(args, 'bwlimit', None):
        config.set('rclone_options', 'bwlimit', args.bwlimit)

    # transfers / checkers 需要修改 copy_flags 字符串
    copy_flags = config.get('rclone_options', 'copy_flags', fallback='')
    if getattr(args, 'transfers', None):
        if re.search(r'--transfers\s+\d+', copy_flags):
            copy_flags = re.sub(r'--transfers\s+\d+',
                                f'--transfers {args.transfers}', copy_flags)
        else:
            copy_flags = copy_flags.rstrip() + f' --transfers {args.transfers}'
    if getattr(args, 'checkers', None):
        if re.search(r'--checkers\s+\d+', copy_flags):
            copy_flags = re.sub(r'--checkers\s+\d+',
                                f'--checkers {args.checkers}', copy_flags)
        else:
            copy_flags = copy_flags.rstrip() + f' --checkers {args.checkers}'

    if getattr(args, 'transfers', None) or getattr(args, 'checkers', None):
        config.set('rclone_options', 'copy_flags', copy_flags)

    return config


def has_rclone_overrides(args) -> bool:
    """检查是否有任何 rclone 覆盖参数被设置"""
    override_attrs = [
        'src_namenode', 'src_username', 'tgt_provider', 'tgt_endpoint',
        'tgt_ak', 'tgt_sk', 'tgt_bucket', 'tgt_path', 'bwlimit', 'transfers', 'checkers',
    ]
    return any(getattr(args, attr, None) is not None for attr in override_attrs)


RCLONE_OVERRIDE_CLI_ARGS = [
    ('--src-namenode', 'src_namenode'),
    ('--src-username', 'src_username'),
    ('--tgt-provider', 'tgt_provider'),
    ('--tgt-endpoint', 'tgt_endpoint'),
    ('--tgt-ak', 'tgt_ak'),
    ('--tgt-sk', 'tgt_sk'),
    ('--tgt-bucket', 'tgt_bucket'),
    ('--tgt-path', 'tgt_path'),
    ('--bwlimit', 'bwlimit'),
    ('--transfers', 'transfers'),
    ('--checkers', 'checkers'),
]


def build_rclone_override_cmd_args(args) -> list:
    """将当前 args 中的 rclone 覆盖参数转换为命令行参数列表，用于后台进程透传"""
    cmd_parts = []
    for flag, attr in RCLONE_OVERRIDE_CLI_ARGS:
        val = getattr(args, attr, None)
        if val is not None:
            cmd_parts.extend([flag, str(val)])
    return cmd_parts


def add_common_args(parser):
    """为 argparse 添加通用参数"""
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('-e', '--explore-dir', help='migration-lhm-inspect-hive-metastore 探查输出目录')
    input_group.add_argument('-d', '--databases', help='数据库名列表，逗号分隔')
    input_group.add_argument('-t', '--tables', help='表名列表 (db.table)，逗号分隔')

    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录')
    parser.add_argument('--filter-db', help='在探查结果上过滤指定数据库，逗号分隔')
    parser.add_argument('--filter-tables', help='在探查结果上过滤指定表，逗号分隔 (db.table)')


def resolve_tables_from_args(args) -> List[TableMeta]:
    """根据命令行参数解析表列表"""
    filter_dbs = [d.strip() for d in args.filter_db.split(',')] if getattr(args, 'filter_db', None) else None
    filter_tables = [t.strip() for t in args.filter_tables.split(',')] if getattr(args, 'filter_tables', None) else None

    if args.explore_dir:
        return load_tables_from_explore_dir(args.explore_dir, filter_dbs, filter_tables)
    elif args.databases:
        dbs = [d.strip() for d in args.databases.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, databases=dbs)
    elif args.tables:
        tbls = [t.strip() for t in args.tables.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, tables_list=tbls)
    else:
        print("错误：必须指定 --explore-dir、--databases 或 --tables")
        sys.exit(1)


def add_common_args(parser):
    """为 argparse 添加通用参数"""
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('-e', '--explore-dir', help='migration-lhm-inspect-hive-metastore 探查输出目录')
    input_group.add_argument('-d', '--databases', help='数据库名列表，逗号分隔')
    input_group.add_argument('-t', '--tables', help='表名列表 (db.table)，逗号分隔')

    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录')
    parser.add_argument('--filter-db', help='在探查结果上过滤指定数据库，逗号分隔')
    parser.add_argument('--filter-tables', help='在探查结果上过滤指定表，逗号分隔 (db.table)')


def resolve_tables_from_args(args) -> List[TableMeta]:
    """根据命令行参数解析表列表"""
    filter_dbs = [d.strip() for d in args.filter_db.split(',')] if getattr(args, 'filter_db', None) else None
    filter_tables = [t.strip() for t in args.filter_tables.split(',')] if getattr(args, 'filter_tables', None) else None

    if args.explore_dir:
        return load_tables_from_explore_dir(args.explore_dir, filter_dbs, filter_tables)
    elif args.databases:
        dbs = [d.strip() for d in args.databases.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, databases=dbs)
    elif args.tables:
        tbls = [t.strip() for t in args.tables.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, tables_list=tbls)
    else:
        print("错误：必须指定 --explore-dir、--databases 或 --tables")
        sys.exit(1)
    filter_tables = [t.strip() for t in args.filter_tables.split(',')] if getattr(args, 'filter_tables', None) else None

    if args.explore_dir:
        return load_tables_from_explore_dir(args.explore_dir, filter_dbs, filter_tables)
    elif args.databases:
        dbs = [d.strip() for d in args.databases.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, databases=dbs)
    elif args.tables:
        tbls = [t.strip() for t in args.tables.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, tables_list=tbls)
    else:
        print("错误：必须指定 --explore-dir、--databases 或 --tables")
        sys.exit(1)
def add_common_args(parser):
    """为 argparse 添加通用参数"""
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('-e', '--explore-dir', help='migration-lhm-inspect-hive-metastore 探查输出目录')
    input_group.add_argument('-d', '--databases', help='数据库名列表，逗号分隔')
    input_group.add_argument('-t', '--tables', help='表名列表 (db.table)，逗号分隔')

    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录')
    parser.add_argument('--filter-db', help='在探查结果上过滤指定数据库，逗号分隔')
    parser.add_argument('--filter-tables', help='在探查结果上过滤指定表，逗号分隔 (db.table)')


def resolve_tables_from_args(args) -> List[TableMeta]:
    """根据命令行参数解析表列表"""
    filter_dbs = [d.strip() for d in args.filter_db.split(',')] if getattr(args, 'filter_db', None) else None
    filter_tables = [t.strip() for t in args.filter_tables.split(',')] if getattr(args, 'filter_tables', None) else None

    if args.explore_dir:
        return load_tables_from_explore_dir(args.explore_dir, filter_dbs, filter_tables)
    elif args.databases:
        dbs = [d.strip() for d in args.databases.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, databases=dbs)
    elif args.tables:
        tbls = [t.strip() for t in args.tables.split(',')]
        config = read_config(args.config, required_sections={
            'metastore_db': ['db_type', 'host', 'port', 'user', 'password', 'database']
        })
        return load_tables_from_metastore(config, tables_list=tbls)
    else:
        print("错误：必须指定 --explore-dir、--databases 或 --tables")
        sys.exit(1)
