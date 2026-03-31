#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_query.py 全分支覆盖测试

运行方式: python test_build_query.py
"""

import json
import sys

# 导入被测试的模块
from build_query import (
    _escape_value,
    _format_value,
    _parse_query_recursive,
    _modality_to_category,
    build_query
)


class TestResults:
    """测试结果统计"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []
    
    def record(self, test_name: str, passed: bool, message: str = ""):
        if passed:
            self.passed += 1
            print(f"  ✓ {test_name}")
        else:
            self.failed += 1
            self.failures.append((test_name, message))
            print(f"  ✗ {test_name}")
            if message:
                print(f"    {message}")
    
    def summary(self):
        print("\n" + "=" * 60)
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败")
        if self.failures:
            print("\n失败的测试:")
            for name, msg in self.failures:
                print(f"  - {name}: {msg}")
        print("=" * 60)
        return self.failed == 0


results = TestResults()


def test_escape_value():
    """测试 _escape_value 函数"""
    print("\n[测试 _escape_value]")
    
    # 普通字符串
    results.record(
        "普通字符串不变",
        _escape_value("hello") == "hello",
        f"期望 'hello', 得到 '{_escape_value('hello')}'"
    )
    
    # 包含双引号
    expected_quote = 'say \\"hello\\"'
    actual_quote = _escape_value('say "hello"')
    results.record(
        "转义双引号",
        actual_quote == expected_quote,
        f"期望 {repr(expected_quote)}, 得到 {repr(actual_quote)}"
    )
    
    # 包含反斜杠
    expected_slash = "path\\\\to\\\\file"
    actual_slash = _escape_value("path\\to\\file")
    results.record(
        "转义反斜杠",
        actual_slash == expected_slash,
        f"期望 {repr(expected_slash)}, 得到 {repr(actual_slash)}"
    )
    
    # 同时包含双引号和反斜杠
    expected = 'a\\\\\\"b'
    actual = _escape_value('a\\"b')
    results.record(
        "转义双引号和反斜杠",
        actual == expected,
        f"期望 {repr(expected)}, 得到 {repr(actual)}"
    )


def test_format_value():
    """测试 _format_value 函数"""
    print("\n[测试 _format_value]")
    
    # string 类型字段 - 加引号
    results.record(
        "string类型字段加引号 (name)",
        _format_value("name", "test.pdf") == '"test.pdf"',
        f"期望 '\"test.pdf\"', 得到 '{_format_value('name', 'test.pdf')}'"
    )
    
    # long 类型字段 - 不加引号
    results.record(
        "long类型字段不加引号 (size)",
        _format_value("size", "1000") == "1000",
        f"期望 '1000', 得到 '{_format_value('size', '1000')}'"
    )
    
    # boolean 类型字段 - 不加引号
    results.record(
        "boolean类型字段不加引号 (hidden)",
        _format_value("hidden", "false") == "false",
        f"期望 'false', 得到 '{_format_value('hidden', 'false')}'"
    )
    
    results.record(
        "boolean类型字段不加引号 (starred)",
        _format_value("starred", "true") == "true",
        f"期望 'true', 得到 '{_format_value('starred', 'true')}'"
    )
    
    # date 类型字段 - 加引号
    results.record(
        "date类型字段加引号 (created_at)",
        _format_value("created_at", "2025-01-01T00:00:00") == '"2025-01-01T00:00:00"',
        f"期望 '\"2025-01-01T00:00:00\"', 得到 '{_format_value('created_at', '2025-01-01T00:00:00')}'"
    )
    
    # 未知字段 - 默认加引号
    results.record(
        "未知字段默认加引号",
        _format_value("unknown_field", "value") == '"value"',
        f"期望 '\"value\"', 得到 '{_format_value('unknown_field', 'value')}'"
    )
    
    # string 类型带转义
    expected_escaped = '"file\\"name"'
    actual_escaped = _format_value("name", 'file"name')
    results.record(
        "string类型带转义",
        actual_escaped == expected_escaped,
        f"期望 {repr(expected_escaped)}, 得到 {repr(actual_escaped)}"
    )


def test_basic_operations():
    """测试基础操作符"""
    print("\n[测试基础操作符]")
    
    # 简单 eq 查询 - string 类型
    query = {"Operation": "eq", "Field": "name", "Value": "test.pdf"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "eq 查询 string 类型带引号",
        result == '(name = "test.pdf")',
        f"期望 '(name = \"test.pdf\")', 得到 '{result}'"
    )
    
    # 简单 eq 查询 - long 类型
    query = {"Operation": "eq", "Field": "size", "Value": "1000"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "eq 查询 long 类型不带引号",
        result == '(size = 1000)',
        f"期望 '(size = 1000)', 得到 '{result}'"
    )
    
    # 简单 eq 查询 - boolean 类型
    query = {"Operation": "eq", "Field": "hidden", "Value": "false"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "eq 查询 boolean 类型不带引号",
        result == '(hidden = false)',
        f"期望 '(hidden = false)', 得到 '{result}'"
    )
    
    # 简单 gte 查询 - date 类型
    query = {"Operation": "gte", "Field": "created_at", "Value": "2025-01-01T00:00:00"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "gte 查询 date 类型带引号",
        result == '(created_at >= "2025-01-01T00:00:00")',
        f"期望 '(created_at >= \"2025-01-01T00:00:00\")', 得到 '{result}'"
    )
    
    # match 操作符
    query = {"Operation": "match", "Field": "name", "Value": "报告"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "match 操作符",
        result == '(name match "报告")',
        f"期望 '(name match \"报告\")', 得到 '{result}'"
    )
    
    # prefix 操作符
    query = {"Operation": "prefix", "Field": "description", "Value": "项目"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "prefix 操作符",
        result == '(description prefix "项目")',
        f"期望 '(description prefix \"项目\")', 得到 '{result}'"
    )


def test_comparison_operators():
    """测试比较操作符"""
    print("\n[测试比较操作符]")
    
    # lt - long 类型不带引号
    query = {"Operation": "lt", "Field": "size", "Value": "1000"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "lt 操作符 (long)",
        result == '(size < 1000)',
        f"期望 '(size < 1000)', 得到 '{result}'"
    )
    
    # lte
    query = {"Operation": "lte", "Field": "size", "Value": "1000"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "lte 操作符",
        result == '(size <= 1000)',
        f"期望 '(size <= 1000)', 得到 '{result}'"
    )
    
    # gt
    query = {"Operation": "gt", "Field": "size", "Value": "1000"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "gt 操作符",
        result == '(size > 1000)',
        f"期望 '(size > 1000)', 得到 '{result}'"
    )
    
    # gte - date 类型带引号
    query = {"Operation": "gte", "Field": "created_at", "Value": "2025-01-01T00:00:00"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "gte 操作符 (date)",
        result == '(created_at >= "2025-01-01T00:00:00")',
        f"期望 '(created_at >= \"2025-01-01T00:00:00\")', 得到 '{result}'"
    )


def test_logical_operators():
    """测试逻辑操作符"""
    print("\n[测试逻辑操作符]")
    
    # and - 多个子查询
    query = {
        "Operation": "and",
        "SubQueries": [
            {"Operation": "eq", "Field": "name", "Value": "test.pdf"},
            {"Operation": "gt", "Field": "size", "Value": "1000"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "and 多个子查询",
        result == '((name = "test.pdf") and (size > 1000))',
        f"期望 '((name = \"test.pdf\") and (size > 1000))', 得到 '{result}'"
    )
    
    # and - 单个子查询（因 category 被移除）
    query = {
        "Operation": "and",
        "SubQueries": [
            {"Operation": "eq", "Field": "category", "Value": "image"},
            {"Operation": "gt", "Field": "size", "Value": "1000"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "and 单个子查询（category被移除）",
        result == '(size > 1000)',
        f"期望 '(size > 1000)', 得到 '{result}'"
    )
    results.record(
        "and 单个子查询 category 被收集",
        cats == {"image"},
        f"期望 {{'image'}}, 得到 {cats}"
    )
    
    # and - 所有子查询都是 category
    query = {
        "Operation": "and",
        "SubQueries": [
            {"Operation": "eq", "Field": "category", "Value": "image"},
            {"Operation": "eq", "Field": "category", "Value": "video"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "and 所有子查询都是category返回空",
        result == "",
        f"期望 '', 得到 '{result}'"
    )
    results.record(
        "and 所有category都被收集",
        cats == {"image", "video"},
        f"期望 {{'image', 'video'}}, 得到 {cats}"
    )
    
    # or - 多个子查询
    query = {
        "Operation": "or",
        "SubQueries": [
            {"Operation": "eq", "Field": "name", "Value": "a.pdf"},
            {"Operation": "eq", "Field": "name", "Value": "b.pdf"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "or 多个子查询",
        result == '((name = "a.pdf") or (name = "b.pdf"))',
        f"期望 '((name = \"a.pdf\") or (name = \"b.pdf\"))', 得到 '{result}'"
    )
    
    # or - 单个子查询
    query = {
        "Operation": "or",
        "SubQueries": [
            {"Operation": "eq", "Field": "category", "Value": "doc"},
            {"Operation": "eq", "Field": "name", "Value": "test.pdf"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "or 单个子查询（category被移除）",
        result == '(name = "test.pdf")',
        f"期望 '(name = \"test.pdf\")', 得到 '{result}'"
    )
    
    # not 操作符
    query = {
        "Operation": "not",
        "SubQueries": [
            {"Operation": "eq", "Field": "hidden", "Value": "true"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "not 操作符",
        result == 'not ((hidden = true))',
        f"期望 'not ((hidden = true))', 得到 '{result}'"
    )
    
    # not - 子查询为 category
    query = {
        "Operation": "not",
        "SubQueries": [
            {"Operation": "eq", "Field": "category", "Value": "image"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "not 子查询为category返回空",
        result == "",
        f"期望 '', 得到 '{result}'"
    )
    
    # 空 SubQueries
    query = {
        "Operation": "and",
        "SubQueries": []
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "空SubQueries返回空",
        result == "",
        f"期望 '', 得到 '{result}'"
    )


def test_category_extraction():
    """测试 Category 提取"""
    print("\n[测试 Category 提取]")
    
    # 单个 category eq
    query = {"Operation": "eq", "Field": "category", "Value": "image"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "单个category eq - 返回空查询",
        result == "",
        f"期望 '', 得到 '{result}'"
    )
    results.record(
        "单个category eq - 收集category",
        cats == {"image"},
        f"期望 {{'image'}}, 得到 {cats}"
    )
    
    # 多个 category 在 or 中
    query = {
        "Operation": "or",
        "SubQueries": [
            {"Operation": "eq", "Field": "category", "Value": "image"},
            {"Operation": "eq", "Field": "category", "Value": "video"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "多个category在or中 - 返回空",
        result == "",
        f"期望 '', 得到 '{result}'"
    )
    results.record(
        "多个category在or中 - 全部收集",
        cats == {"image", "video"},
        f"期望 {{'image', 'video'}}, 得到 {cats}"
    )
    
    # category 混合其他条件
    query = {
        "Operation": "and",
        "SubQueries": [
            {"Operation": "eq", "Field": "category", "Value": "doc"},
            {"Operation": "gt", "Field": "size", "Value": "1000"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    results.record(
        "category混合其他条件 - 只返回其他条件",
        result == "(size > 1000)",
        f"期望 '(size > 1000)', 得到 '{result}'"
    )
    results.record(
        "category混合其他条件 - category被提取",
        cats == {"doc"},
        f"期望 {{'doc'}}, 得到 {cats}"
    )


def test_nested_queries():
    """测试嵌套查询"""
    print("\n[测试嵌套查询]")
    
    # 两层嵌套: and[or[A, B], C]
    query = {
        "Operation": "and",
        "SubQueries": [
            {
                "Operation": "or",
                "SubQueries": [
                    {"Operation": "eq", "Field": "name", "Value": "a.pdf"},
                    {"Operation": "eq", "Field": "name", "Value": "b.pdf"}
                ]
            },
            {"Operation": "gt", "Field": "size", "Value": "1000"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    expected = '(((name = "a.pdf") or (name = "b.pdf")) and (size > 1000))'
    results.record(
        "两层嵌套 and[or[A,B], C]",
        result == expected,
        f"期望 '{expected}', 得到 '{result}'"
    )
    
    # 三层嵌套
    query = {
        "Operation": "or",
        "SubQueries": [
            {
                "Operation": "and",
                "SubQueries": [
                    {"Operation": "eq", "Field": "type", "Value": "file"},
                    {
                        "Operation": "or",
                        "SubQueries": [
                            {"Operation": "eq", "Field": "file_extension", "Value": "pdf"},
                            {"Operation": "eq", "Field": "file_extension", "Value": "docx"}
                        ]
                    }
                ]
            },
            {"Operation": "eq", "Field": "hidden", "Value": "false"}
        ]
    }
    result, cats = _parse_query_recursive(query)
    # 验证结果包含正确的结构
    results.record(
        "三层嵌套查询",
        "type" in result and "file_extension" in result and "hidden" in result,
        f"得到 '{result}'"
    )


def test_semantic_queries():
    """测试语义查询"""
    print("\n[测试语义查询]")
    
    # 纯语义查询
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": "海边日落", "modality": ["image"]}
    })
    result = build_query(None, semantic_json)
    results.record(
        "纯语义查询",
        result["has_query"] == True and 'semantic_text = "海边日落"' in result["query"],
        f"得到 query: {result.get('query')}"
    )
    results.record(
        "纯语义查询含category",
        "category" in result["query"],
        f"得到 query: {result.get('query')}"
    )
    
    # 语义查询中的特殊字符转义
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": '说"你好"的照片', "modality": ["all"]}
    })
    result = build_query(None, semantic_json)
    results.record(
        "语义查询特殊字符转义",
        result["has_query"] == True and '\\"' in result["query"],
        f"得到 query: {result.get('query')}"
    )


def test_category_modality_merge():
    """测试 Category 和 Modality 合并"""
    print("\n[测试 Category/Modality 合并]")
    
    # 标量 category + 语义 modality 合并
    scalar_json = json.dumps({
        "valid": True,
        "result": {"Query": {"Operation": "eq", "Field": "category", "Value": "doc"}}
    })
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": "合同", "modality": ["video"]}
    })
    result = build_query(scalar_json, semantic_json)
    results.record(
        "category + modality 合并为 in",
        "category in" in result["query"] and "doc" in result["query"] and "video" in result["query"],
        f"得到 query: {result.get('query')}"
    )
    
    # 语义 modality=["all"] 不添加 category
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": "风景", "modality": ["all"]}
    })
    result = build_query(None, semantic_json)
    results.record(
        "modality=all 不添加category",
        "category" not in result["query"],
        f"得到 query: {result.get('query')}"
    )
    
    # 仅语义有 modality
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": "会议", "modality": ["document"]}
    })
    result = build_query(None, semantic_json)
    results.record(
        "仅语义有modality",
        result["has_query"] == True and "category" in result["query"] and "doc" in result["query"],
        f"得到 query: {result.get('query')}"
    )
    
    # 仅标量有 category
    scalar_json = json.dumps({
        "valid": True,
        "result": {
            "Query": {
                "Operation": "and",
                "SubQueries": [
                    {"Operation": "eq", "Field": "category", "Value": "image"},
                    {"Operation": "gt", "Field": "size", "Value": "1000"}
                ]
            }
        }
    })
    result = build_query(scalar_json, None)
    results.record(
        "仅标量有category",
        result["has_query"] == True and "category" in result["query"] and "image" in result["query"],
        f"得到 query: {result.get('query')}"
    )


def test_combined_scalar_semantic():
    """测试标量+语义组合查询"""
    print("\n[测试标量+语义组合]")
    
    scalar_json = json.dumps({
        "valid": True,
        "result": {"Query": {"Operation": "gt", "Field": "size", "Value": "1000"}}
    })
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": "风景照片", "modality": ["image"]}
    })
    result = build_query(scalar_json, semantic_json)
    results.record(
        "标量+语义组合",
        result["has_query"] == True and "size > 1000" in result["query"] and "semantic_text" in result["query"],
        f"得到 query: {result.get('query')}"
    )


def test_edge_cases():
    """测试边界情况"""
    print("\n[测试边界情况]")
    
    # 两个查询都 valid=false
    scalar_json = json.dumps({"valid": False})
    semantic_json = json.dumps({"valid": False})
    result = build_query(scalar_json, semantic_json)
    results.record(
        "两个查询都invalid",
        result["has_query"] == False and result["message"] is not None,
        f"得到 has_query: {result.get('has_query')}, message: {result.get('message')[:30]}..."
    )
    
    # 只有标量 valid
    scalar_json = json.dumps({
        "valid": True,
        "result": {"Query": {"Operation": "eq", "Field": "name", "Value": "test.pdf"}}
    })
    semantic_json = json.dumps({"valid": False})
    result = build_query(scalar_json, semantic_json)
    results.record(
        "只有标量valid",
        result["has_query"] == True and "name" in result["query"],
        f"得到 query: {result.get('query')}"
    )
    
    # 只有语义 valid
    scalar_json = json.dumps({"valid": False})
    semantic_json = json.dumps({
        "valid": True,
        "result": {"query": "日落", "modality": ["all"]}
    })
    result = build_query(scalar_json, semantic_json)
    results.record(
        "只有语义valid",
        result["has_query"] == True and "semantic_text" in result["query"],
        f"得到 query: {result.get('query')}"
    )
    
    # 未知字段默认加引号
    query = {"Operation": "eq", "Field": "unknown_custom_field", "Value": "test"}
    result_str, cats = _parse_query_recursive(query)
    results.record(
        "未知字段默认加引号",
        result_str == '(unknown_custom_field = "test")',
        f"期望 '(unknown_custom_field = \"test\")', 得到 '{result_str}'"
    )
    
    # JSON 解析失败
    result = build_query("invalid json", None)
    results.record(
        "JSON解析失败处理",
        result["has_query"] == False,
        f"得到 has_query: {result.get('has_query')}"
    )
    
    # None 输入
    result = build_query(None, None)
    results.record(
        "None输入处理",
        result["has_query"] == False,
        f"得到 has_query: {result.get('has_query')}"
    )


def test_sort_order():
    """测试 Sort 和 Order 处理"""
    print("\n[测试 Sort/Order]")
    
    # 单字段排序
    scalar_json = json.dumps({
        "valid": True,
        "result": {
            "Query": {"Operation": "eq", "Field": "type", "Value": "file"},
            "Sort": "size",
            "Order": "desc"
        }
    })
    result = build_query(scalar_json, None)
    results.record(
        "单字段排序",
        result["order_by"] == "size DESC",
        f"期望 'size DESC', 得到 '{result.get('order_by')}'"
    )
    
    # 多字段排序
    scalar_json = json.dumps({
        "valid": True,
        "result": {
            "Query": {"Operation": "eq", "Field": "type", "Value": "file"},
            "Sort": "size,name",
            "Order": "desc,asc"
        }
    })
    result = build_query(scalar_json, None)
    results.record(
        "多字段排序",
        result["order_by"] == "size DESC,name ASC",
        f"期望 'size DESC,name ASC', 得到 '{result.get('order_by')}'"
    )
    
    # Order 数量少于 Sort（默认 ASC）
    scalar_json = json.dumps({
        "valid": True,
        "result": {
            "Query": {"Operation": "eq", "Field": "type", "Value": "file"},
            "Sort": "size,name",
            "Order": "desc"
        }
    })
    result = build_query(scalar_json, None)
    results.record(
        "Order数量少于Sort默认ASC",
        result["order_by"] == "size DESC,name ASC",
        f"期望 'size DESC,name ASC', 得到 '{result.get('order_by')}'"
    )
    
    # 无效 Order 值默认 ASC
    scalar_json = json.dumps({
        "valid": True,
        "result": {
            "Query": {"Operation": "eq", "Field": "type", "Value": "file"},
            "Sort": "size",
            "Order": "invalid"
        }
    })
    result = build_query(scalar_json, None)
    results.record(
        "无效Order默认ASC",
        result["order_by"] == "size ASC",
        f"期望 'size ASC', 得到 '{result.get('order_by')}'"
    )
    
    # 只有 Sort 没有 Order
    scalar_json = json.dumps({
        "valid": True,
        "result": {
            "Sort": "name"
        }
    })
    result = build_query(scalar_json, None)
    results.record(
        "只有Sort无Order",
        result["order_by"] == "name ASC",
        f"期望 'name ASC', 得到 '{result.get('order_by')}'"
    )


def test_modality_to_category():
    """测试 modality 到 category 的映射"""
    print("\n[测试 modality 映射]")
    
    results.record(
        "document -> doc",
        _modality_to_category("document") == "doc",
        f"得到 '{_modality_to_category('document')}'"
    )
    results.record(
        "image -> image",
        _modality_to_category("image") == "image",
        f"得到 '{_modality_to_category('image')}'"
    )
    results.record(
        "video -> video",
        _modality_to_category("video") == "video",
        f"得到 '{_modality_to_category('video')}'"
    )
    results.record(
        "audio -> audio",
        _modality_to_category("audio") == "audio",
        f"得到 '{_modality_to_category('audio')}'"
    )
    results.record(
        "all -> None",
        _modality_to_category("all") is None,
        f"得到 '{_modality_to_category('all')}'"
    )
    results.record(
        "大小写不敏感 IMAGE -> image",
        _modality_to_category("IMAGE") == "image",
        f"得到 '{_modality_to_category('IMAGE')}'"
    )


def test_unknown_operation():
    """测试未知操作符"""
    print("\n[测试未知操作符]")
    
    query = {"Operation": "unknown_op", "Field": "name", "Value": "test"}
    result, cats = _parse_query_recursive(query)
    results.record(
        "未知操作符返回空",
        result == "",
        f"期望 '', 得到 '{result}'"
    )


def test_single_part_query():
    """测试单一部分查询（去掉外层括号）"""
    print("\n[测试单一部分查询]")
    
    # 只有标量查询
    scalar_json = json.dumps({
        "valid": True,
        "result": {"Query": {"Operation": "eq", "Field": "name", "Value": "test.pdf"}}
    })
    result = build_query(scalar_json, None)
    # 只有一个部分时，应该去掉外层括号
    results.record(
        "单一标量查询去掉外层括号",
        result["query"] == 'name = "test.pdf"',
        f"期望 'name = \"test.pdf\"', 得到 '{result.get('query')}'"
    )


def main():
    """运行所有测试"""
    print("=" * 60)
    print("build_query.py 全分支覆盖测试")
    print("=" * 60)
    
    # 运行所有测试
    test_escape_value()
    test_format_value()
    test_basic_operations()
    test_comparison_operators()
    test_logical_operators()
    test_category_extraction()
    test_nested_queries()
    test_semantic_queries()
    test_category_modality_merge()
    test_combined_scalar_semantic()
    test_edge_cases()
    test_sort_order()
    test_modality_to_category()
    test_unknown_operation()
    test_single_part_query()
    
    # 输出结果
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
