#!/usr/bin/env python3
"""
[评测工具] get_table_schema - 查询目标 DB 中表的列信息

Usage:
    python get_table_schema.py --tables dm.store_week edw.orders --target odps

Output:
    JSON: { "dm.store_week": [{"column":"col1","type":"STRING"}, ...], ... }

Environment:
    ENV_DIR  配置文件目录
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import get_table_schema

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--tables", nargs="+", required=True)
    p.add_argument("--target", required=True, choices=["odps", "hologres"])
    args = p.parse_args()

    result = get_table_schema(args.tables, args.target)
    if result is None:
        print(json.dumps({}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
