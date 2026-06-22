#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""华为云 vs 阿里云 ECS + 数据库 价格对比脚本 (中国大陆区域)"""

import requests
import json
import time
import re

PRICING_URL = "http://localhost:5001/api/pricing/batch"
REGION_ID = "cn-beijing"  # 阿里云北京区域

# ================================================================
# 华为云 ECS 参考价格 (华北-北京四, 包月, Linux, 不含磁盘)
# 数据来源: 华为云官方价格计算器 (2025年参考值)
# ================================================================
HW_ECS_SPECS = {
    # 计算型 c7 (1:2 比例)
    "c7.large.2":    {"vcpu": 2,  "mem": 4,   "hw_price": 259,    "type": "计算型c7",  "ali_family": "ecs.c7"},
    "c7.xlarge.2":   {"vcpu": 4,  "mem": 8,   "hw_price": 518,    "type": "计算型c7",  "ali_family": "ecs.c7"},
    "c7.2xlarge.2":  {"vcpu": 8,  "mem": 16,  "hw_price": 1036,   "type": "计算型c7",  "ali_family": "ecs.c7"},
    "c7.4xlarge.2":  {"vcpu": 16, "mem": 32,  "hw_price": 2072,   "type": "计算型c7",  "ali_family": "ecs.c7"},
    "c7.8xlarge.2":  {"vcpu": 32, "mem": 64,  "hw_price": 4144,   "type": "计算型c7",  "ali_family": "ecs.c7"},
    # 通用型 s7 (1:4 比例)
    "s7.large.4":    {"vcpu": 2,  "mem": 8,   "hw_price": 338,    "type": "通用型s7",  "ali_family": "ecs.g7"},
    "s7.xlarge.4":   {"vcpu": 4,  "mem": 16,  "hw_price": 676,    "type": "通用型s7",  "ali_family": "ecs.g7"},
    "s7.2xlarge.4":  {"vcpu": 8,  "mem": 32,  "hw_price": 1352,   "type": "通用型s7",  "ali_family": "ecs.g7"},
    "s7.4xlarge.4":  {"vcpu": 16, "mem": 64,  "hw_price": 2704,   "type": "通用型s7",  "ali_family": "ecs.g7"},
    "s7.8xlarge.4":  {"vcpu": 32, "mem": 128, "hw_price": 5408,   "type": "通用型s7",  "ali_family": "ecs.g7"},
    # 内存型 m7 (1:8 比例)
    "m7.large.8":    {"vcpu": 2,  "mem": 16,  "hw_price": 498,    "type": "内存型m7",  "ali_family": "ecs.r7"},
    "m7.xlarge.8":   {"vcpu": 4,  "mem": 32,  "hw_price": 996,    "type": "内存型m7",  "ali_family": "ecs.r7"},
    "m7.2xlarge.8":  {"vcpu": 8,  "mem": 64,  "hw_price": 1992,   "type": "内存型m7",  "ali_family": "ecs.r7"},
    "m7.4xlarge.8":  {"vcpu": 16, "mem": 128, "hw_price": 3984,   "type": "内存型m7",  "ali_family": "ecs.r7"},
    # ARM 鲲鹏 kc1 (1:2 比例) → 阿里云倚天 c8y
    "kc1.large.2":   {"vcpu": 2,  "mem": 4,   "hw_price": 198,    "type": "ARM鲲鹏kc1", "ali_family": "ecs.c8y"},
    "kc1.xlarge.2":  {"vcpu": 4,  "mem": 8,   "hw_price": 396,    "type": "ARM鲲鹏kc1", "ali_family": "ecs.c8y"},
    "kc1.2xlarge.2": {"vcpu": 8,  "mem": 16,  "hw_price": 792,    "type": "ARM鲲鹏kc1", "ali_family": "ecs.c8y"},
    "kc1.4xlarge.2": {"vcpu": 16, "mem": 32,  "hw_price": 1584,   "type": "ARM鲲鹏kc1", "ali_family": "ecs.c8y"},
    # ARM 通用型 km1 (1:4 比例) → 阿里云倚天 g8y
    "km1.large.4":   {"vcpu": 2,  "mem": 8,   "hw_price": 268,    "type": "ARM通用km1",  "ali_family": "ecs.g8y"},
    "km1.xlarge.4":  {"vcpu": 4,  "mem": 16,  "hw_price": 536,    "type": "ARM通用km1",  "ali_family": "ecs.g8y"},
    "km1.2xlarge.4": {"vcpu": 8,  "mem": 32,  "hw_price": 1072,   "type": "ARM通用km1",  "ali_family": "ecs.g8y"},
    # 突发型 t6 (1:2 比例)
    "t6.medium.2":   {"vcpu": 1,  "mem": 2,   "hw_price": 46,     "type": "突发型t6",  "ali_family": "ecs.t6"},
    "t6.large.2":    {"vcpu": 2,  "mem": 4,   "hw_price": 92,     "type": "突发型t6",  "ali_family": "ecs.t6"},
    "t6.xlarge.4":   {"vcpu": 2,  "mem": 8,   "hw_price": 138,    "type": "突发型t6",  "ali_family": "ecs.t6-c1m2"},
}

# ECS size mapping
ALI_SIZE_MAP = {1: "large", 2: "large", 4: "xlarge", 8: "2xlarge", 16: "4xlarge", 32: "8xlarge"}

def get_ali_ecs_spec(ali_family, vcpu):
    size = ALI_SIZE_MAP.get(vcpu, f"{vcpu//4}xlarge" if vcpu > 4 else "large")
    return f"{ali_family}.{size}"

# ================================================================
# 华为云 RDS MySQL 参考价格 (华北-北京四, 包月, 含100GB SSD存储)
# ================================================================
HW_RDS_SPECS = {
    # (vCPU, 内存GB): (华为云RDS月价, 阿里云MySQL规格, 阿里云product_code)
    (1, 2):    {"hw_price": 136,   "ali_spec": "rds.mysql.s1.small",    "product": "rds"},
    (2, 4):    {"hw_price": 268,   "ali_spec": "rds.mysql.s2.large",    "product": "rds"},
    (2, 8):    {"hw_price": 378,   "ali_spec": "rds.mysql.s2.xlarge",   "product": "rds"},
    (4, 8):    {"hw_price": 536,   "ali_spec": "rds.mysql.s3.small",    "product": "rds"},
    (4, 16):   {"hw_price": 756,   "ali_spec": "rds.mysql.s3.large",    "product": "rds"},
    (8, 16):   {"hw_price": 1072,  "ali_spec": "rds.mysql.c1.medium",   "product": "rds"},
    (8, 32):   {"hw_price": 1512,  "ali_spec": "rds.mysql.m1.medium",   "product": "rds"},
    (16, 32):  {"hw_price": 2144,  "ali_spec": "rds.mysql.c1.xlarge",   "product": "rds"},
    (16, 64):  {"hw_price": 3024,  "ali_spec": "rds.mysql.m1.xlarge",   "product": "rds"},
    (32, 128): {"hw_price": 6048,  "ali_spec": "rds.mysql.m1.2xlarge",  "product": "rds"},
    (64, 256): {"hw_price": 12096, "ali_spec": "rds.mysql.m1.4xlarge",  "product": "rds"},
}

# ================================================================
# 华为云 GaussDB for MySQL → 阿里云 PolarDB MySQL
# ================================================================
HW_GAUSSDB_SPECS = {
    (2, 8):    {"hw_price": 698,    "ali_spec": "polar.mysql.g2.xlarge",   "product": "polardb"},
    (4, 16):   {"hw_price": 1396,   "ali_spec": "polar.mysql.g4.xlarge",   "product": "polardb"},
    (8, 32):   {"hw_price": 2792,   "ali_spec": "polar.mysql.g8.xlarge",   "product": "polardb"},
    (8, 64):   {"hw_price": 3968,   "ali_spec": "polar.mysql.g8.2xlarge",  "product": "polardb"},
    (16, 64):  {"hw_price": 5584,   "ali_spec": "polar.mysql.g8.2xlarge",  "product": "polardb"},
    (16, 128): {"hw_price": 7936,   "ali_spec": "polar.mysql.g8.4xlarge",  "product": "polardb"},
    (32, 256): {"hw_price": 15872,  "ali_spec": "polar.mysql.g8.8xlarge",  "product": "polardb"},
    (64, 512): {"hw_price": 31744,  "ali_spec": "polar.mysql.g8.16xlarge", "product": "polardb"},
}


def batch_query(specs_with_product):
    """批量查询阿里云价格，返回 {spec: price} 字典"""
    items = []
    for spec, product in specs_with_product:
        items.append({
            "product_code": product,
            "instance_spec": spec,
            "region_id": REGION_ID,
            "period": 1,
            "quantity": 1
        })
    results = {}
    batch_size = 5
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        try:
            resp = requests.post(PRICING_URL, json={"items": batch}, timeout=60)
            data = resp.json()
            if data.get("success") and "data" in data:
                for p in data["data"].get("prices", []):
                    if p.get("success"):
                        results[p["instance_spec"]] = p.get("trade_price", 0)
        except Exception as e:
            print(f"  询价批次失败: {e}")
        time.sleep(0.3)
    return results


def main():
    print("=" * 150)
    print("华为云 vs 阿里云 价格对比报告 (中国大陆区域)")
    print("华为云: 华北-北京四 | 阿里云: cn-beijing (华北2-北京)")
    print("=" * 150)

    # ===== Part 1: ECS 对比 =====
    print("\n" + "=" * 150)
    print("一、ECS 虚拟机价格对比 (包年包月 1个月)")
    print("=" * 150)

    # 构建阿里云ECS规格列表
    ecs_query_list = []
    hw_to_ali_ecs = {}
    for hw_spec, info in HW_ECS_SPECS.items():
        ali_spec = get_ali_ecs_spec(info["ali_family"], info["vcpu"])
        hw_to_ali_ecs[hw_spec] = ali_spec
        ecs_query_list.append((ali_spec, "ecs"))

    # 去重
    unique_ecs = list(set(ecs_query_list))
    print(f"\n正在查询 {len(unique_ecs)} 个阿里云ECS规格的实时价格 (cn-beijing)...")
    ecs_prices = batch_query(unique_ecs)
    print(f"成功获取 {len(ecs_prices)} 个ECS规格价格\n")

    header = f"{'华为云规格':<18} {'类型':<14} {'vCPU':>4} {'内存GB':>6} {'华为云月价':>10} {'阿里云ECS规格':<22} {'阿里云月价':>10} {'价差':>8} {'阿里云节省%':>10}"
    print(header)
    print("-" * 150)

    type_order = ["计算型c7", "通用型s7", "内存型m7", "ARM鲲鹏kc1", "ARM通用km1", "突发型t6"]
    last_type = ""
    sorted_items = sorted(HW_ECS_SPECS.items(),
                          key=lambda x: (type_order.index(x[1]["type"]) if x[1]["type"] in type_order else 99,
                                         x[1]["vcpu"], x[1]["mem"]))

    for hw_spec, info in sorted_items:
        if info["type"] != last_type:
            if last_type:
                print()
            last_type = info["type"]

        ali_spec = hw_to_ali_ecs[hw_spec]
        ali_price = ecs_prices.get(ali_spec, 0)
        hw_price = info["hw_price"]

        if ali_price > 0:
            diff = ali_price - hw_price
            save_pct = (1 - ali_price / hw_price) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"

        print(f"{hw_spec:<18} {info['type']:<14} {info['vcpu']:>4} {info['mem']:>6} "
              f"{hw_price:>10.0f} {ali_spec:<22} {ali_price:>10.0f} {diff_str:>8} {save_str:>10}")

    # ===== Part 2: RDS 数据库对比 =====
    print("\n\n" + "=" * 150)
    print("二、RDS MySQL 数据库价格对比 (包年包月 1个月)")
    print("=" * 150)

    rds_query = [(v["ali_spec"], v["product"]) for v in HW_RDS_SPECS.values()]
    unique_rds = list(set(rds_query))
    print(f"\n正在查询 {len(unique_rds)} 个阿里云RDS规格的实时价格 (cn-beijing)...")
    rds_prices = batch_query(unique_rds)
    print(f"成功获取 {len(rds_prices)} 个RDS规格价格\n")

    header = f"{'华为云RDS规格':<16} {'vCPU':>4} {'内存GB':>6} {'华为云月价':>10} {'阿里云RDS规格':<26} {'阿里云月价':>10} {'价差':>8} {'阿里云节省%':>10}"
    print(header)
    print("-" * 150)

    for (vcpu, mem), info in sorted(HW_RDS_SPECS.items(), key=lambda x: (x[0][0], x[0][1])):
        hw_spec_name = f"rds.mysql {vcpu}C{mem}G"
        ali_spec = info["ali_spec"]
        ali_price = rds_prices.get(ali_spec, 0)
        hw_price = info["hw_price"]

        if ali_price > 0:
            diff = ali_price - hw_price
            save_pct = (1 - ali_price / hw_price) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"

        print(f"{hw_spec_name:<16} {vcpu:>4} {mem:>6} "
              f"{hw_price:>10.0f} {ali_spec:<26} {ali_price:>10.0f} {diff_str:>8} {save_str:>10}")

    # ===== Part 3: GaussDB vs PolarDB 对比 =====
    print("\n\n" + "=" * 150)
    print("三、GaussDB for MySQL vs PolarDB MySQL 价格对比 (包年包月 1个月)")
    print("=" * 150)

    gaussdb_query = [(v["ali_spec"], v["product"]) for v in HW_GAUSSDB_SPECS.values()]
    unique_gaussdb = list(set(gaussdb_query))
    print(f"\n正在查询 {len(unique_gaussdb)} 个阿里云PolarDB规格的实时价格 (cn-beijing)...")
    gaussdb_prices = batch_query(unique_gaussdb)
    print(f"成功获取 {len(gaussdb_prices)} 个PolarDB规格价格\n")

    header = f"{'华为GaussDB规格':<18} {'vCPU':>4} {'内存GB':>6} {'华为云月价':>10} {'阿里云PolarDB规格':<28} {'阿里云月价':>10} {'价差':>8} {'阿里云节省%':>10}"
    print(header)
    print("-" * 150)

    for (vcpu, mem), info in sorted(HW_GAUSSDB_SPECS.items(), key=lambda x: (x[0][0], x[0][1])):
        hw_spec_name = f"gaussdb {vcpu}C{mem}G"
        ali_spec = info["ali_spec"]
        ali_price = gaussdb_prices.get(ali_spec, 0)
        hw_price = info["hw_price"]

        if ali_price > 0:
            diff = ali_price - hw_price
            save_pct = (1 - ali_price / hw_price) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"

        print(f"{hw_spec_name:<18} {vcpu:>4} {mem:>6} "
              f"{hw_price:>10.0f} {ali_spec:<28} {ali_price:>10.0f} {diff_str:>8} {save_str:>10}")

    print("\n" + "=" * 150)
    print("说明:")
    print("1. 华为云价格为华北-北京四区域参考价(包年包月1个月, Linux, 仅计算资源不含磁盘)")
    print("   * 华为云价格来源: 官方价格计算器参考值，实际价格请以华为云控制台为准")
    print("2. 阿里云价格为cn-beijing区域实时询价(包年包月1个月, 不含系统盘)")
    print("3. '阿里云节省%'为正表示阿里云更便宜，为负表示阿里云更贵")
    print("4. 两家均有包年折扣: 包年约85折, 3年约5折")
    print("5. 华为云GaussDB为分布式数据库, 阿里云PolarDB为云原生数据库, 架构有差异")
    print("=" * 150)


if __name__ == "__main__":
    main()
