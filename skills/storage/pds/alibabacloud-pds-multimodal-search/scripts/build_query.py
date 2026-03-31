#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 PDS SearchFile API 查询字符串

将标量查询 JSON 和语义查询 JSON 拼接为 SearchFile API 的 query 字符串。
支持递归解析嵌套查询条件，合并 modality 和 category 条件。

用法:
    python build_query.py --scalar-json '<json>' --semantic-json '<json>'
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional, List, Set, Tuple

from get_scalar_query_prompt import field_schema


def _escape_value(value: str) -> str:
    """转义查询字符串中的特殊字符（反斜杠和双引号）"""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_value(field: str, value: str) -> str:
    """
    根据字段类型格式化值。
    
    Args:
        field: 字段名
        value: 字段值
        
    Returns:
        格式化后的值字符串（string/date 类型加引号，long/boolean 不加引号）
    """
    # 获取字段类型，未知字段默认为 string
    field_info = field_schema.get(field.lower(), {})
    field_type = field_info.get("type", "string")
    
    # long 和 boolean 类型不加引号
    if field_type in ("long", "boolean"):
        return str(value)
    
    # string 和 date 类型加引号，并转义
    escaped = _escape_value(str(value))
    return f'"{escaped}"'


def _parse_query_recursive(query: Dict[str, Any]) -> Tuple[str, Set[str]]:
    """
    递归解析 Query 对象为查询字符串。
    
    Args:
        query: Query JSON 对象
        
    Returns:
        (查询字符串, 提取到的 category 值集合)
    """
    operation = query.get("Operation", "").lower()
    categories_found: Set[str] = set()
    
    # 操作符映射
    op_map = {
        "lt": "<",
        "lte": "<=",
        "eq": "=",
        "gt": ">",
        "gte": ">=",
        "match": "match",
        "prefix": "prefix"
    }
    
    # 逻辑操作符处理 SubQueries
    if operation in ("and", "or", "not"):
        sub_queries = query.get("SubQueries", [])
        if not sub_queries:
            return "", categories_found
        
        sub_parts = []
        for sub in sub_queries:
            sub_str, sub_cats = _parse_query_recursive(sub)
            categories_found.update(sub_cats)
            # 过滤空字符串（category 被移除后会产生空字符串）
            if sub_str:
                sub_parts.append(sub_str)
        
        # 过滤后判断子查询数量
        if not sub_parts:
            return "", categories_found
        
        if operation == "not":
            # not 操作对子查询取反
            return f"not ({sub_parts[0]})", categories_found
        elif len(sub_parts) == 1:
            # 只有一个子查询，直接返回，不需要逻辑操作符
            return sub_parts[0], categories_found
        else:
            # 多个子查询，用逻辑操作符连接
            joined = f" {operation} ".join(sub_parts)
            return f"({joined})", categories_found
    
    # 比较/匹配操作符
    if operation in op_map:
        field = query.get("Field", "")
        value = query.get("Value", "")
        api_op = op_map[operation]
        
        # category 条件：收集并返回空字符串（在递归中移除）
        if field.lower() == "category":
            categories_found.add(value)
            return "", categories_found
        
        # 根据字段类型格式化值
        formatted_value = _format_value(field, value)
        return f"({field} {api_op} {formatted_value})", categories_found
    
    return "", categories_found



def _modality_to_category(modality: str) -> Optional[str]:
    """
    将 modality 映射为 category。
    
    Args:
        modality: 模态类型
        
    Returns:
        对应的 category 值，如果是 all 则返回 None
    """
    mapping = {
        "document": "doc",
        "doc": "doc",
        "image": "image",
        "video": "video",
        "audio": "audio"
    }
    return mapping.get(modality.lower())


def build_query(
    scalar_json: Optional[str],
    semantic_json: Optional[str]
) -> Dict[str, Any]:
    """
    构建最终的查询结果。
    
    Args:
        scalar_json: 标量查询 JSON 字符串
        semantic_json: 语义查询 JSON 字符串
        
    Returns:
        包含 has_query, query, order_by, message 的结果字典
    """
    scalar_data = None
    semantic_data = None
    
    # 解析标量查询
    if scalar_json:
        try:
            scalar_data = json.loads(scalar_json)
        except json.JSONDecodeError as e:
            print(f"[WARN] 标量查询 JSON 解析失败: {e}", file=sys.stderr)
    
    # 解析语义查询
    if semantic_json:
        try:
            semantic_data = json.loads(semantic_json)
        except json.JSONDecodeError as e:
            print(f"[WARN] 语义查询 JSON 解析失败: {e}", file=sys.stderr)
    
    # 检查是否有有效查询
    scalar_valid = scalar_data and scalar_data.get("valid", False)
    semantic_valid = semantic_data and semantic_data.get("valid", False)
    
    if not scalar_valid and not semantic_valid:
        return {
            "has_query": False,
            "query": None,
            "order_by": None,
            "message": "很抱歉，我暂时无法理解您的搜索意图。目前支持以下搜索方式：\n1. 按文件属性搜索：如文件名、类型、大小、创建时间等\n2. 按内容语义搜索：如描述文件内容、场景等\n\n请尝试更具体地描述您想查找的文件，例如：\n- \"查找去年的PDF文档\"\n- \"海边日落的照片\"\n- \"大于10MB的视频文件\""
        }
    
    query_parts: List[str] = []
    all_categories: Set[str] = set()
    
    # 处理标量查询
    scalar_query_str = ""
    if scalar_valid:
        result = scalar_data.get("result", {})
        query_obj = result.get("Query")
        
        if query_obj:
            # 递归解析，同时收集 category 条件（category 在递归中被移除）
            scalar_query_str, cats_from_scalar = _parse_query_recursive(query_obj)
            all_categories.update(cats_from_scalar)
    
    # 处理语义查询
    semantic_query_str = ""
    if semantic_valid:
        result = semantic_data.get("result", {})
        query_text = result.get("query", "")
        modalities = result.get("modality", ["all"])
        
        if query_text:
            escaped_text = _escape_value(query_text)
            semantic_query_str = f'semantic_text = "{escaped_text}"'
        
        # 从 modality 收集 category
        for m in modalities:
            cat = _modality_to_category(m)
            if cat:
                all_categories.add(cat)
    
    # 构建合并后的 category 条件
    category_str = ""
    if all_categories:
        if len(all_categories) == 1:
            cat = list(all_categories)[0]
            escaped_cat = _escape_value(cat)
            category_str = f'category = "{escaped_cat}"'
        else:
            # 多个 category 使用 in 操作符
            cats_list = sorted(list(all_categories))
            escaped_cats = [f'"{_escape_value(c)}"' for c in cats_list]
            category_str = f'category in [{", ".join(escaped_cats)}]'
    
    # 最终拼接
    if scalar_query_str:
        query_parts.append(scalar_query_str)
    if semantic_query_str:
        query_parts.append(f"({semantic_query_str})")
    if category_str:
        query_parts.append(f"({category_str})")
    
    # 如果只有一个部分
    if len(query_parts) == 1:
        part = query_parts[0]
        # 如果是单个括号包裹的表达式，去掉外层括号
        if part.startswith("(") and part.endswith(")"):
            final_query = part[1:-1]
        else:
            final_query = part
    else:
        final_query = " and ".join(query_parts)
    
    # 处理排序
    order_by = None
    if scalar_valid:
        result = scalar_data.get("result", {})
        sort_field = result.get("Sort")
        order_direction = result.get("Order", "")
        
        if sort_field:
            # 处理多字段排序
            sort_fields = [f.strip() for f in sort_field.split(",")]
            order_directions = [d.strip().upper() for d in order_direction.split(",")] if order_direction else []
            
            order_parts = []
            for i, field in enumerate(sort_fields):
                direction = order_directions[i] if i < len(order_directions) else "ASC"
                if direction not in ("ASC", "DESC"):
                    direction = "ASC"
                order_parts.append(f"{field} {direction}")
            
            order_by = ",".join(order_parts)
    
    return {
        "has_query": True,
        "query": final_query if final_query else None,
        "order_by": order_by,
        "message": None
    }


def main():
    parser = argparse.ArgumentParser(
        description="将标量查询和语义查询 JSON 拼接为 SearchFile API 的 query 字符串",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 仅标量查询
  python build_query.py --scalar-json '{"valid": true, "result": {"Query": {"Operation": "gte", "Field": "size", "Value": "1000"}}}'

  # 仅语义查询
  python build_query.py --semantic-json '{"valid": true, "result": {"query": "海边日落", "modality": ["image"]}}'

  # 混合查询
  python build_query.py \\
    --scalar-json '{"valid": true, "result": {"Query": {"Operation": "gt", "Field": "size", "Value": "1000"}, "Sort": "size", "Order": "desc"}}' \\
    --semantic-json '{"valid": true, "result": {"query": "风景照片", "modality": ["image"]}}'

输出格式:
  {
    "has_query": true,
    "query": "拼接后的查询字符串",
    "order_by": "size DESC",
    "message": null
  }
"""
    )
    
    parser.add_argument(
        "--scalar-json",
        default=None,
        help="标量查询的 JSON 字符串，包含 valid 和 result 字段"
    )
    parser.add_argument(
        "--semantic-json",
        default=None,
        help="语义查询的 JSON 字符串，包含 valid 和 result 字段"
    )
    
    args = parser.parse_args()
    
    # 输入校验
    if not args.scalar_json and not args.semantic_json:
        print("[INFO] 未提供任何查询参数", file=sys.stderr)
    
    # 构建查询
    result = build_query(args.scalar_json, args.semantic_json)
    
    # 输出结果到 stdout
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
