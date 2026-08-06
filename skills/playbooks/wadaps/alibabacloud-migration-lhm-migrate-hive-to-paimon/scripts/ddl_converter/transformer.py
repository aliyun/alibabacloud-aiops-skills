"""Hive DDL 到 DLF DDL 的转换逻辑。"""

import re
import sys
from dataclasses import dataclass
from typing import Optional, List, Tuple

from parser import HiveTable, Column


# SERDE 类名 -> DLF FORMAT 映射（包含匹配）
SERDE_MAP = {
    "OrcSerde": "ORC",
    "LazySimpleSerDe": "CSV",
    "ParquetHiveSerDe": "PARQUET",
    "AvroSerDe": "AVRO",
    "JsonSerDe": "JSON",
}

# INPUTFORMAT 类名 -> DLF FORMAT 映射（备选）
INPUT_FORMAT_MAP = {
    "OrcInputFormat": "ORC",
    "TextInputFormat": "CSV",
    "MapredParquetInputFormat": "PARQUET",
    "AvroContainerInputFormat": "AVRO",
}


@dataclass
class ExtConfig:
    """外表生成配置。"""
    source_hdfs_nameservice: str
    oss_bucket: str
    oss_prefix: str
    ext_table_prefix: str = "ext_"
    default_format: str = "ORC"


def detect_format(table: HiveTable, default_format: str = "ORC") -> Tuple[str, List[str]]:
    """根据 SERDE / INPUTFORMAT 检测存储格式。返回 (format, warnings)。"""
    warnings = []

    # 优先从 SERDE 判断
    if table.serde_class:
        for key, fmt in SERDE_MAP.items():
            if key in table.serde_class:
                return fmt, warnings

    # 回退到 INPUTFORMAT
    if table.input_format:
        for key, fmt in INPUT_FORMAT_MAP.items():
            if key in table.input_format:
                return fmt, warnings

    # 都没有，使用默认值并输出警告
    warnings.append(
        f"WARNING: {table.database}.{table.table_name} 未检测到 SERDE/INPUTFORMAT 信息，"
        f"默认使用 {default_format}"
    )
    return default_format, warnings


def to_paimon(table: HiveTable) -> Tuple[str, List[str]]:
    """将 HiveTable 转换为 Paimon 内表 DDL。返回 (ddl_str, warnings)。"""
    warnings = []
    lines = []

    # CREATE TABLE IF NOT EXISTS db.table(
    lines.append(f"CREATE TABLE IF NOT EXISTS {table.database}.{table.table_name}(")

    # 字段列表：去反引号，保留小写，保留 COMMENT
    # Paimon 内表：分区字段同时出现在字段列表和 PARTITIONED BY 中
    partition_names = {pc.name for pc in table.partition_columns}
    all_cols = list(table.columns)
    # 将不在字段列表中的分区字段追加到末尾
    for pc in table.partition_columns:
        if pc.name not in {c.name for c in table.columns}:
            all_cols.append(pc)

    for i, col in enumerate(all_cols):
        is_last = (i == len(all_cols) - 1)
        line = f"  {col.name} {col.type}"
        if col.comment is not None:
            line += f" COMMENT '{col.comment}'"
        if not is_last:
            line += ","
        else:
            line += ")"
        lines.append(line)

    # USING paimon
    lines.append("USING paimon")

    # 表级 COMMENT
    if table.table_comment:
        lines.append(f"COMMENT '{table.table_comment}'")

    # PARTITIONED BY（仅字段名，带反引号，不含类型）
    if table.partition_columns:
        part_names = ", ".join(f"`{pc.name}`" for pc in table.partition_columns)
        lines.append(f"PARTITIONED BY (")
        # 每个分区字段单独一行
        for i, pc in enumerate(table.partition_columns):
            is_last = (i == len(table.partition_columns) - 1)
            if is_last:
                lines.append(f"  `{pc.name}`);")
            else:
                lines.append(f"  `{pc.name}`,")
    else:
        # 无分区表：最后一行加分号
        lines[-1] += ";"

    return "\n".join(lines), warnings


def _map_path(location: str, config: ExtConfig) -> Tuple[str, List[str]]:
    """HDFS 路径映射为 OSS 路径。返回 (oss_path, warnings)。"""
    warnings = []

    # 去除 hdfs://{nameservice} 前缀，获取相对路径
    prefix = f"hdfs://{config.source_hdfs_nameservice}"
    if location.startswith(prefix):
        relative_path = location[len(prefix):]
    else:
        # 尝试匹配其他 hdfs:// 格式
        m = re.match(r'hdfs://[^/]+(/.+)', location)
        if m:
            relative_path = m.group(1)
            warnings.append(
                f"WARNING: 非标准 LOCATION 路径，请确认 OSS 路径正确"
            )
        else:
            relative_path = location
            warnings.append(
                f"WARNING: 无法解析 LOCATION 路径: {location}"
            )

    oss_path = f"oss://{config.oss_bucket}/{config.oss_prefix}{relative_path}"
    return oss_path, warnings


def _upper_type(col_type: str) -> str:
    """字段类型统一大写，保留 decimal(x,y) 括号内数字。"""
    return col_type.upper()


def to_external(table: HiveTable, config: ExtConfig) -> Tuple[str, List[str]]:
    """将 HiveTable 转换为 FORMAT 外表 DDL。返回 (ddl_str, warnings)。"""
    all_warnings = []
    lines = []

    # 检测格式
    fmt, fmt_warnings = detect_format(table, config.default_format)
    all_warnings.extend(fmt_warnings)

    # 外表名
    ext_table = f"{table.database}.{config.ext_table_prefix}{table.table_name}"

    # CREATE TABLE db.ext_table (
    lines.append(f"CREATE TABLE {ext_table} (")

    # 字段列表：去反引号，类型大写，无 COMMENT
    # 分区字段不出现在字段列表中
    partition_names = {pc.name for pc in table.partition_columns}
    non_partition_cols = [c for c in table.columns if c.name not in partition_names]

    for i, col in enumerate(non_partition_cols):
        is_last = (i == len(non_partition_cols) - 1)
        line = f"    {col.name} {_upper_type(col.type)}"
        if not is_last:
            line += ","
        lines.append(line)

    lines.append(")")

    # USING {FORMAT}
    lines.append(f"USING {fmt}")

    # PARTITIONED BY（含类型，大写）
    if table.partition_columns:
        lines.append("PARTITIONED BY (")
        for i, pc in enumerate(table.partition_columns):
            is_last = (i == len(table.partition_columns) - 1)
            line = f"    {pc.name} {_upper_type(pc.type)}"
            if not is_last:
                line += ","
            lines.append(line)
        lines.append(")")

    # OPTIONS('path'='...')
    if table.location:
        oss_path, path_warnings = _map_path(table.location, config)
        all_warnings.extend(path_warnings)
        lines.append("OPTIONS(")
        lines.append(f"'path'='{oss_path}'")
        lines.append(");")
    else:
        all_warnings.append(
            f"WARNING: {table.database}.{table.table_name} 无 LOCATION 信息，无法生成 OPTIONS"
        )
        lines.append(");")

    return "\n".join(lines), all_warnings
