#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PolarDB MySQL 实例健康巡检脚本
通过 aliyun CLI 调用 PolarDB API 和 DAS API 完成全面巡检

Usage:
    python3 health-inspect.py <cluster_id> [options]

Examples:
    python3 health-inspect.py pc-bp1715bzkcrateo69
    python3 health-inspect.py pc-bp1715bzkcrateo69 --region cn-hangzhou
    python3 health-inspect.py pc-bp1715bzkcrateo69 --profile myprofile --output ./report.txt
"""
import sys
import os

# 确保从任何工作目录执行时都能找到 hi_* 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hi_main import main

if __name__ == '__main__':
    main()
