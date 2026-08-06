"""Hive DDL 解析器 - 从 Hive CREATE TABLE 语句中提取结构信息。"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Column:
    """字段定义。"""
    name: str
    type: str
    comment: Optional[str] = None


@dataclass
class HiveTable:
    """解析后的 Hive 表结构。"""
    database: str
    table_name: str
    columns: List[Column] = field(default_factory=list)
    table_comment: Optional[str] = None
    partition_columns: List[Column] = field(default_factory=list)
    serde_class: Optional[str] = None
    input_format: Optional[str] = None
    location: Optional[str] = None


def parse_ddl(ddl_text: str) -> List[HiveTable]:
    """解析一条或多条 Hive DDL，返回 HiveTable 列表。"""
    statements = split_statements(ddl_text)
    tables = []
    for stmt in statements:
        table = parse_single_statement(stmt)
        if table:
            tables.append(table)
    return tables


def split_statements(ddl_text: str) -> List[str]:
    """按 CREATE TABLE 关键字分割多条 DDL 语句。"""
    parts = re.split(r'(?=\bCREATE\s+)', ddl_text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def parse_single_statement(stmt: str) -> Optional[HiveTable]:
    """解析单条 Hive DDL 语句。"""
    # 检查是否为 CREATE TABLE 语句
    if not re.search(r'\bCREATE\s+(?:EXTERNAL\s+)?TABLE\b', stmt, re.IGNORECASE):
        return None

    database, table_name = _extract_table_name(stmt)
    if not database or not table_name:
        return None

    columns = _extract_columns(stmt)
    table_comment = _extract_table_comment(stmt)
    partition_columns = _extract_partition_columns(stmt)
    serde_class = _extract_serde(stmt)
    input_format = _extract_input_format(stmt)
    location = _extract_location(stmt)

    return HiveTable(
        database=database,
        table_name=table_name,
        columns=columns,
        table_comment=table_comment,
        partition_columns=partition_columns,
        serde_class=serde_class,
        input_format=input_format,
        location=location,
    )


def _extract_table_name(stmt: str) -> tuple:
    """提取 db.table 格式的表名。"""
    m = re.search(
        r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+[`"]?(\w+)[`"]?\s*\.\s*[`"]?(\w+)[`"]?',
        stmt, re.IGNORECASE
    )
    if m:
        return m.group(1), m.group(2)
    # 尝试不带 db 的表名
    m = re.search(
        r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+[`"]?(\w+)[`"]?\s*\(',
        stmt, re.IGNORECASE
    )
    if m:
        return '', m.group(1)
    return None, None


def _extract_columns(stmt: str) -> List[Column]:
    """用括号深度计数法提取字段列表。"""
    # 找到表名后的第一个 '('
    m = re.search(
        r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+[^(]+\(',
        stmt, re.IGNORECASE
    )
    if not m:
        return []

    start = m.end() - 1  # 定位到 '('
    col_block = _extract_balanced_parens(stmt, start)
    if not col_block:
        return []

    return _parse_column_block(col_block)


def _extract_balanced_parens(text: str, start: int) -> Optional[str]:
    """从 start 位置的 '(' 开始，提取括号内容（不含外层括号）。"""
    if start >= len(text) or text[start] != '(':
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


def _parse_column_block(block: str) -> List[Column]:
    """解析字段块中的各字段定义。"""
    columns = []
    # 按顶层逗号分割（不拆分括号内的逗号，如 decimal(15,2)）
    parts = _split_by_top_comma(block)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        col = _parse_single_column(part)
        if col:
            columns.append(col)
    return columns


def _split_by_top_comma(text: str) -> List[str]:
    """按顶层逗号分割，忽略括号内的逗号。"""
    parts = []
    depth = 0
    current = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            current.append(ch)
            escape_next = False
            continue

        if ch == '\\':
            current.append(ch)
            escape_next = True
            continue

        if ch == "'" and not in_string:
            in_string = True
            current.append(ch)
            continue
        elif ch == "'" and in_string:
            in_string = False
            current.append(ch)
            continue

        if in_string:
            current.append(ch)
            continue

        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1

        if ch == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)

    if current:
        parts.append(''.join(current))

    return parts


def _parse_single_column(col_str: str) -> Optional[Column]:
    """解析单个字段定义，如 `col_name` type COMMENT 'xxx'。"""
    col_str = col_str.strip()
    if not col_str:
        return None

    # 提取 COMMENT（可选）
    comment = None
    comment_match = re.search(r"\bCOMMENT\s+'((?:[^'\\]|'')*)'", col_str, re.IGNORECASE)
    if comment_match:
        comment = comment_match.group(1)
        col_str = col_str[:comment_match.start()].strip()

    # 剩余部分：`name` type 或 name type
    # 去除反引号
    col_str = col_str.replace('`', '').strip()

    # 分割字段名和类型
    parts = col_str.split(None, 1)
    if len(parts) < 2:
        return None

    name = parts[0].strip()
    col_type = parts[1].strip()

    # 清理类型末尾可能的多余内容
    col_type = re.sub(r'\s+$', '', col_type)

    return Column(name=name, type=col_type, comment=comment)


def _extract_table_comment(stmt: str) -> Optional[str]:
    """提取表级 COMMENT（在字段列表闭括号之后，PARTITIONED BY 之前）。"""
    # 找到字段列表闭括号的位置
    m = re.search(
        r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+[^(]+\(',
        stmt, re.IGNORECASE
    )
    if not m:
        return None

    start = m.end() - 1
    # 用括号计数找到闭括号
    depth = 0
    close_pos = -1
    for i in range(start, len(stmt)):
        if stmt[i] == '(':
            depth += 1
        elif stmt[i] == ')':
            depth -= 1
            if depth == 0:
                close_pos = i
                break

    if close_pos == -1:
        return None

    # 在闭括号之后查找 COMMENT，但在 PARTITIONED BY / ROW FORMAT / STORED AS / LOCATION 之前
    after_cols = stmt[close_pos + 1:]
    # 截取到下一个关键子句
    end_match = re.search(
        r'\b(?:PARTITIONED\s+BY|ROW\s+FORMAT|STORED\s+AS|LOCATION|TBLPROPERTIES)\b',
        after_cols, re.IGNORECASE
    )
    if end_match:
        search_area = after_cols[:end_match.start()]
    else:
        search_area = after_cols

    comment_match = re.search(r"\bCOMMENT\s+'((?:[^'\\]|'')*)'", search_area, re.IGNORECASE)
    if comment_match:
        return comment_match.group(1)
    return None


def _extract_partition_columns(stmt: str) -> List[Column]:
    """提取 PARTITIONED BY (...) 中的分区列。"""
    m = re.search(r'\bPARTITIONED\s+BY\s*\(', stmt, re.IGNORECASE)
    if not m:
        return []

    start = stmt.index('(', m.start())
    block = _extract_balanced_parens(stmt, start)
    if not block:
        return []

    columns = []
    parts = _split_by_top_comma(block)
    for part in parts:
        part = part.strip().replace('`', '')
        if not part:
            continue
        pieces = part.split(None, 1)
        if len(pieces) >= 2:
            name = pieces[0].strip()
            col_type = pieces[1].strip()
            # 去掉可能的 COMMENT
            comment_match = re.search(r"\bCOMMENT\s+'((?:[^'\\]|'')*)'", col_type, re.IGNORECASE)
            if comment_match:
                col_type = col_type[:comment_match.start()].strip()
            columns.append(Column(name=name, type=col_type))
        elif len(pieces) == 1:
            columns.append(Column(name=pieces[0].strip(), type='string'))
    return columns


def _extract_serde(stmt: str) -> Optional[str]:
    """提取 ROW FORMAT SERDE 'xxx' 中的类全名。"""
    m = re.search(r"ROW\s+FORMAT\s+SERDE\s+'([^']+)'", stmt, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_input_format(stmt: str) -> Optional[str]:
    """提取 STORED AS INPUTFORMAT 'xxx' 中的类全名。"""
    m = re.search(r"STORED\s+AS\s+INPUTFORMAT\s+'([^']+)'", stmt, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_location(stmt: str) -> Optional[str]:
    """提取 LOCATION 'xxx' 中的路径。"""
    m = re.search(r"LOCATION\s+'([^']+)'", stmt, re.IGNORECASE)
    return m.group(1) if m else None
