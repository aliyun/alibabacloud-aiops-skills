#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DDL 重建引擎

从 Hive Metastore Thrift 的 Table 对象还原 CREATE TABLE DDL 语句。
"""

# InputFormat/OutputFormat → STORED AS 简写映射
_FORMAT_MAP = {
    ('org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
     'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'): 'PARQUET',
    ('org.apache.hadoop.hive.ql.io.orc.OrcInputFormat',
     'org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat'): 'ORC',
    ('org.apache.hadoop.mapred.TextInputFormat',
     'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'): 'TEXTFILE',
    ('org.apache.hadoop.mapred.SequenceFileInputFormat',
     'org.apache.hadoop.hive.ql.io.HiveSequenceFileOutputFormat'): 'SEQUENCEFILE',
    ('org.apache.hadoop.hive.ql.io.avro.AvroContainerInputFormat',
     'org.apache.hadoop.hive.ql.io.avro.AvroContainerOutputFormat'): 'AVRO',
    ('org.apache.hadoop.hive.ql.io.RCFileInputFormat',
     'org.apache.hadoop.hive.ql.io.RCFileOutputFormat'): 'RCFILE',
}

# STORED AS 简写对应的默认 SerDe
_DEFAULT_SERDE = {
    'PARQUET': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
    'ORC': 'org.apache.hadoop.hive.ql.io.orc.OrcSerde',
    'TEXTFILE': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
    'SEQUENCEFILE': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
    'AVRO': 'org.apache.hadoop.hive.serde2.avro.AvroSerDe',
    'RCFILE': 'org.apache.hadoop.hive.serde2.columnar.ColumnarSerDe',
}

# TBLPROPERTIES 中需要过滤的内部键
_INTERNAL_PROPS = {
    'transient_lastDdlTime', 'COLUMN_STATS_ACCURATE',
    'totalSize', 'rawDataSize', 'numFiles', 'numRows',
    'last_modified_time', 'last_modified_by',
    'EXTERNAL', 'bucketing_version', 'numFilesErasureCoded',
    'TRANSLATED_TO_EXTERNAL',
}

# SerDe properties 中需要过滤的内部键
_INTERNAL_SERDE_PROPS = {
    'serialization.format', 'serialization.lib',
}

# LazySimpleSerDe 的分隔符参数映射
_DELIM_KEYS = {
    'field.delim': 'FIELDS TERMINATED BY',
    'collection.delim': 'COLLECTION ITEMS TERMINATED BY',
    'mapkey.delim': 'MAP KEYS TERMINATED BY',
    'line.delim': 'LINES TERMINATED BY',
}


def _escape_str(s):
    """转义 SQL 字符串中的单引号"""
    if s is None:
        return ''
    return s.replace("'", "\\'")


def _format_col(col):
    """格式化列定义"""
    parts = [f"  `{col.name}` {col.type}"]
    if col.comment:
        parts.append(f"COMMENT '{_escape_str(col.comment)}'")
    return ' '.join(parts)


def _build_storage_clause(sd):
    """
    根据 StorageDescriptor 构建存储格式子句。

    返回多行字符串，包含 ROW FORMAT 和 STORED AS 信息。
    """
    lines = []
    input_fmt = sd.inputFormat or ''
    output_fmt = sd.outputFormat or ''
    serde_info = sd.serdeInfo

    serde_lib = ''
    serde_params = {}
    if serde_info:
        serde_lib = serde_info.serializationLib or ''
        serde_params = dict(serde_info.parameters) if serde_info.parameters else {}

    # 查找是否为已知格式
    format_key = (input_fmt, output_fmt)
    shorthand = _FORMAT_MAP.get(format_key)

    if shorthand:
        default_serde = _DEFAULT_SERDE.get(shorthand, '')
        if serde_lib == default_serde or not serde_lib:
            # LazySimpleSerDe 的 TEXTFILE/SEQUENCEFILE 需要检查分隔符
            if serde_lib == 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe':
                delim_lines = _build_delimited_clause(serde_params)
                if delim_lines:
                    lines.append('ROW FORMAT DELIMITED')
                    lines.extend(delim_lines)
                    # 如果有非分隔符的自定义 serde properties
                    extra_props = _get_user_serde_props(serde_params, exclude_delim=True)
                    if extra_props:
                        lines.append(_format_serde_props(extra_props))
            lines.append(f"STORED AS {shorthand}")
        else:
            # 自定义 SerDe + 已知格式
            lines.append(f"ROW FORMAT SERDE")
            lines.append(f"  '{serde_lib}'")
            user_props = _get_user_serde_props(serde_params)
            if user_props:
                lines.append(_format_serde_props(user_props))
            lines.append(f"STORED AS {shorthand}")
    else:
        # 未知格式组合，使用完整形式
        if serde_lib:
            is_lazy_simple = serde_lib == 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
            if is_lazy_simple:
                delim_lines = _build_delimited_clause(serde_params)
                if delim_lines:
                    lines.append('ROW FORMAT DELIMITED')
                    lines.extend(delim_lines)
                else:
                    lines.append(f"ROW FORMAT SERDE")
                    lines.append(f"  '{serde_lib}'")
                    user_props = _get_user_serde_props(serde_params)
                    if user_props:
                        lines.append(_format_serde_props(user_props))
            else:
                lines.append(f"ROW FORMAT SERDE")
                lines.append(f"  '{serde_lib}'")
                user_props = _get_user_serde_props(serde_params)
                if user_props:
                    lines.append(_format_serde_props(user_props))

        if input_fmt and output_fmt:
            lines.append(f"STORED AS INPUTFORMAT")
            lines.append(f"  '{input_fmt}'")
            lines.append(f"OUTPUTFORMAT")
            lines.append(f"  '{output_fmt}'")

    return '\n'.join(lines)


def _build_delimited_clause(serde_params):
    """从 serde 参数构建 ROW FORMAT DELIMITED 的子句"""
    lines = []
    for param_key, sql_keyword in _DELIM_KEYS.items():
        val = serde_params.get(param_key)
        if val and val != '\x00':
            # 将特殊字符转义显示
            display_val = repr(val)[1:-1] if len(val) == 1 and not val.isprintable() else val
            lines.append(f"  {sql_keyword} '{_escape_str(val)}'")
    return lines


def _get_user_serde_props(serde_params, exclude_delim=False):
    """获取用户自定义的 SerDe 属性（过滤内部键）"""
    skip_keys = set(_INTERNAL_SERDE_PROPS)
    if exclude_delim:
        skip_keys.update(_DELIM_KEYS.keys())
    return {k: v for k, v in serde_params.items()
            if k not in skip_keys}


def _format_serde_props(props):
    """格式化 WITH SERDEPROPERTIES"""
    pairs = [f"    '{_escape_str(k)}' = '{_escape_str(v)}'" for k, v in sorted(props.items())]
    return "WITH SERDEPROPERTIES (\n" + ',\n'.join(pairs) + "\n)"


def build_ddl(table):
    """
    从 Thrift Table 对象重建 CREATE TABLE DDL。

    参数:
        table: hive_metastore.ttypes.Table 对象

    返回:
        str: 完整的 CREATE TABLE DDL 语句
    """
    parts = []

    # 1. 表类型前缀
    tbl_type = getattr(table, 'tableType', '') or ''
    if tbl_type == 'EXTERNAL_TABLE':
        parts.append(f"CREATE EXTERNAL TABLE `{table.dbName}`.`{table.tableName}`(")
    else:
        parts.append(f"CREATE TABLE `{table.dbName}`.`{table.tableName}`(")

    # 2. 列定义
    sd = table.sd
    if sd is None:
        return f"-- WARNING: 表 {table.dbName}.{table.tableName} 没有 StorageDescriptor，无法生成 DDL"

    cols = sd.cols or []
    col_defs = [_format_col(c) for c in cols]
    parts.append(',\n'.join(col_defs))
    parts.append(')')

    # 3. 表注释
    params = dict(table.parameters) if table.parameters else {}
    comment = params.get('comment')
    if comment:
        parts.append(f"COMMENT '{_escape_str(comment)}'")

    # 4. 分区子句
    partition_keys = table.partitionKeys or []
    if partition_keys:
        pk_defs = [_format_col(pk) for pk in partition_keys]
        parts.append('PARTITIONED BY (')
        parts.append(',\n'.join(pk_defs))
        parts.append(')')

    # 5. 分桶子句
    bucket_cols = sd.bucketCols or []
    if bucket_cols:
        bucket_str = ', '.join([f"`{c}`" for c in bucket_cols])
        cluster_line = f"CLUSTERED BY ({bucket_str})"

        sort_cols = sd.sortCols or []
        if sort_cols:
            sort_parts = []
            for sc in sort_cols:
                order = 'ASC' if getattr(sc, 'order', 1) == 1 else 'DESC'
                sort_parts.append(f"`{sc.col}` {order}")
            cluster_line += f" SORTED BY ({', '.join(sort_parts)})"

        num_buckets = sd.numBuckets or 0
        if num_buckets > 0:
            cluster_line += f" INTO {num_buckets} BUCKETS"

        parts.append(cluster_line)

    # 6. 存储格式
    storage_clause = _build_storage_clause(sd)
    if storage_clause:
        parts.append(storage_clause)

    # 7. LOCATION
    location = sd.location
    if location:
        parts.append(f"LOCATION\n  '{location}'")

    # 8. TBLPROPERTIES
    user_props = {k: v for k, v in params.items() if k not in _INTERNAL_PROPS}
    if user_props:
        prop_pairs = [f"  '{_escape_str(k)}' = '{_escape_str(v)}'" for k, v in sorted(user_props.items())]
        parts.append("TBLPROPERTIES (\n" + ',\n'.join(prop_pairs) + "\n)")

    return '\n'.join(parts) + ';\n'
