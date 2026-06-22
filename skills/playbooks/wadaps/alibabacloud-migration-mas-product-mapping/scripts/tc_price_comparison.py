#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""腾讯云 vs 阿里云 CVM + 数据库 价格对比脚本 (中国大陆区域)"""

import requests
import json
import time

PRICING_URL = "http://localhost:5001/api/pricing/batch"
REGION_ID = "cn-beijing"

# ================================================================
# 腾讯云 CVM 参考价格 (北京, 包月, Linux, 不含数据盘)
# 数据来源: 腾讯云官方定价页 https://buy.cloud.tencent.com/price/cvm/overview
# ================================================================
TC_CVM_SPECS = {
    # 标准型 S5 (1:4 比例) → 阿里云通用型 g7
    "S5.MEDIUM8":    {"vcpu": 2,  "mem": 8,   "tc_price": 216.11,  "type": "标准型S5",  "ali_family": "ecs.g7"},
    "S5.LARGE16":    {"vcpu": 4,  "mem": 16,  "tc_price": 432.22,  "type": "标准型S5",  "ali_family": "ecs.g7"},
    "S5.2XLARGE32":  {"vcpu": 8,  "mem": 32,  "tc_price": 864.43,  "type": "标准型S5",  "ali_family": "ecs.g7"},
    "S5.4XLARGE64":  {"vcpu": 16, "mem": 64,  "tc_price": 1728.86, "type": "标准型S5",  "ali_family": "ecs.g7"},
    "S5.8XLARGE128": {"vcpu": 32, "mem": 128, "tc_price": 3457.73, "type": "标准型S5",  "ali_family": "ecs.g7"},
    # 计算型 C5 (1:2 比例) → 阿里云计算型 c7
    "C5.LARGE8":     {"vcpu": 4,  "mem": 8,   "tc_price": 360.00,  "type": "计算型C5",  "ali_family": "ecs.c7"},
    "C5.2XLARGE16":  {"vcpu": 8,  "mem": 16,  "tc_price": 720.00,  "type": "计算型C5",  "ali_family": "ecs.c7"},
    "C5.4XLARGE32":  {"vcpu": 16, "mem": 32,  "tc_price": 1440.00, "type": "计算型C5",  "ali_family": "ecs.c7"},
    "C5.8XLARGE64":  {"vcpu": 32, "mem": 64,  "tc_price": 2880.00, "type": "计算型C5",  "ali_family": "ecs.c7"},
    # 内存型 M5 (1:8 比例) → 阿里云内存型 r7
    "M5.LARGE32":    {"vcpu": 4,  "mem": 32,  "tc_price": 633.60,  "type": "内存型M5",  "ali_family": "ecs.r7"},
    "M5.2XLARGE64":  {"vcpu": 8,  "mem": 64,  "tc_price": 1267.20, "type": "内存型M5",  "ali_family": "ecs.r7"},
    "M5.4XLARGE128": {"vcpu": 16, "mem": 128, "tc_price": 2534.40, "type": "内存型M5",  "ali_family": "ecs.r7"},
}

# ECS size mapping (vCPU → 阿里云尺寸)
ALI_SIZE_MAP = {1: "large", 2: "large", 4: "xlarge", 8: "2xlarge", 16: "4xlarge", 32: "8xlarge", 64: "16xlarge"}

def get_ali_ecs_spec(ali_family, vcpu):
    size = ALI_SIZE_MAP.get(vcpu, f"{vcpu//4}xlarge" if vcpu > 4 else "large")
    return f"{ali_family}.{size}"

# ================================================================
# 腾讯云 CDB MySQL 参考价格 (北京, 双节点通用型, 包月, 不含存储)
# 数据来源: 腾讯云官方定价页
# ================================================================
TC_CDB_SPECS = {
    (1, 2):    {"tc_price": 204,   "ali_spec": "rds.mysql.s1.small",    "product": "rds"},
    (2, 4):    {"tc_price": 408,   "ali_spec": "rds.mysql.s2.large",    "product": "rds"},
    (4, 8):    {"tc_price": 816,   "ali_spec": "rds.mysql.s3.small",    "product": "rds"},
    (4, 16):   {"tc_price": 1632,  "ali_spec": "rds.mysql.s3.large",    "product": "rds"},
    (8, 16):   {"tc_price": 1948,  "ali_spec": "rds.mysql.c1.medium",   "product": "rds"},
    (8, 32):   {"tc_price": 3264,  "ali_spec": "rds.mysql.m1.medium",   "product": "rds"},
    (8, 64):   {"tc_price": 5696,  "ali_spec": "rds.mysql.st8.8xlarge", "product": "rds"},
}

# ================================================================
# 腾讯云 TDSQL-C MySQL → 阿里云 PolarDB MySQL
# 数据来源: 腾讯云官方定价页 (独享型)
# ================================================================
TC_TDSQLC_SPECS = {
    (2, 4):    {"tc_price": 326.40,  "ali_spec": "polar.mysql.g2.medium",   "product": "polardb"},
    (2, 8):    {"tc_price": 470.40,  "ali_spec": "polar.mysql.g2.xlarge",   "product": "polardb"},
    (4, 16):   {"tc_price": 940.80,  "ali_spec": "polar.mysql.g4.xlarge",   "product": "polardb"},
    (8, 32):   {"tc_price": 1881.60, "ali_spec": "polar.mysql.g8.xlarge",   "product": "polardb"},
    (8, 64):   {"tc_price": 3033.60, "ali_spec": "polar.mysql.g8.2xlarge",  "product": "polardb"},
    (16, 64):  {"tc_price": 3763.20, "ali_spec": "polar.mysql.g8.2xlarge",  "product": "polardb"},
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
    print("腾讯云 vs 阿里云 价格对比报告 (中国大陆区域)")
    print("腾讯云: 华北地区-北京 | 阿里云: cn-beijing (华北2-北京)")
    print("=" * 150)

    # ===== Part 1: CVM vs ECS 对比 =====
    print("\n" + "=" * 150)
    print("一、CVM vs ECS 虚拟机价格对比 (包年包月 1个月)")
    print("=" * 150)

    ecs_query_list = []
    tc_to_ali_ecs = {}
    for tc_spec, info in TC_CVM_SPECS.items():
        ali_spec = get_ali_ecs_spec(info["ali_family"], info["vcpu"])
        tc_to_ali_ecs[tc_spec] = ali_spec
        ecs_query_list.append((ali_spec, "ecs"))

    unique_ecs = list(set(ecs_query_list))
    print(f"\n正在查询 {len(unique_ecs)} 个阿里云ECS规格的实时价格 (cn-beijing)...")
    ecs_prices = batch_query(unique_ecs)
    print(f"成功获取 {len(ecs_prices)} 个ECS规格价格\n")

    header = f"{'腾讯云CVM规格':<18} {'类型':<12} {'vCPU':>4} {'内存GB':>6} {'腾讯云月价':>10} {'阿里云ECS规格':<22} {'阿里云月价':>10} {'价差':>8} {'阿里云节省%':>10}"
    print(header)
    print("-" * 150)

    type_order = ["标准型S5", "计算型C5", "内存型M5"]
    last_type = ""
    sorted_items = sorted(TC_CVM_SPECS.items(),
                          key=lambda x: (type_order.index(x[1]["type"]) if x[1]["type"] in type_order else 99,
                                         x[1]["vcpu"], x[1]["mem"]))

    for tc_spec, info in sorted_items:
        if info["type"] != last_type:
            if last_type:
                print()
            last_type = info["type"]

        ali_spec = tc_to_ali_ecs[tc_spec]
        ali_price = ecs_prices.get(ali_spec, 0)
        tc_price = info["tc_price"]

        if ali_price > 0:
            diff = ali_price - tc_price
            save_pct = (1 - ali_price / tc_price) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"

        print(f"{tc_spec:<18} {info['type']:<12} {info['vcpu']:>4} {info['mem']:>6} "
              f"{tc_price:>10.2f} {ali_spec:<22} {ali_price:>10.2f} {diff_str:>8} {save_str:>10}")

    # ===== Part 2: CDB MySQL vs RDS MySQL 对比 =====
    print("\n\n" + "=" * 150)
    print("二、CDB MySQL vs RDS MySQL 数据库价格对比 (包年包月 1个月, 双节点通用型)")
    print("=" * 150)

    rds_query = [(v["ali_spec"], v["product"]) for v in TC_CDB_SPECS.values()]
    unique_rds = list(set(rds_query))
    print(f"\n正在查询 {len(unique_rds)} 个阿里云RDS规格的实时价格 (cn-beijing)...")
    rds_prices = batch_query(unique_rds)
    print(f"成功获取 {len(rds_prices)} 个RDS规格价格\n")

    header = f"{'腾讯CDB规格':<16} {'vCPU':>4} {'内存GB':>6} {'腾讯云月价':>10} {'阿里云RDS规格':<28} {'阿里云月价':>10} {'价差':>8} {'阿里云节省%':>10}"
    print(header)
    print("-" * 150)

    for (vcpu, mem), info in sorted(TC_CDB_SPECS.items(), key=lambda x: (x[0][0], x[0][1])):
        tc_spec_name = f"CDB {vcpu}C{mem}G"
        ali_spec = info["ali_spec"]
        ali_price = rds_prices.get(ali_spec, 0)
        tc_price = info["tc_price"]

        if ali_price > 0:
            diff = ali_price - tc_price
            save_pct = (1 - ali_price / tc_price) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"

        print(f"{tc_spec_name:<16} {vcpu:>4} {mem:>6} "
              f"{tc_price:>10.0f} {ali_spec:<28} {ali_price:>10.0f} {diff_str:>8} {save_str:>10}")

    # ===== Part 3: TDSQL-C MySQL vs PolarDB MySQL 对比 =====
    print("\n\n" + "=" * 150)
    print("三、TDSQL-C MySQL vs PolarDB MySQL 价格对比 (包年包月 1个月, 独享型)")
    print("=" * 150)

    tdsqlc_query = [(v["ali_spec"], v["product"]) for v in TC_TDSQLC_SPECS.values()]
    unique_tdsqlc = list(set(tdsqlc_query))
    print(f"\n正在查询 {len(unique_tdsqlc)} 个阿里云PolarDB规格的实时价格 (cn-beijing)...")
    tdsqlc_prices = batch_query(unique_tdsqlc)
    print(f"成功获取 {len(tdsqlc_prices)} 个PolarDB规格价格\n")

    header = f"{'腾讯TDSQL-C规格':<18} {'vCPU':>4} {'内存GB':>6} {'腾讯云月价':>10} {'阿里云PolarDB规格':<28} {'阿里云月价':>10} {'价差':>8} {'阿里云节省%':>10}"
    print(header)
    print("-" * 150)

    for (vcpu, mem), info in sorted(TC_TDSQLC_SPECS.items(), key=lambda x: (x[0][0], x[0][1])):
        tc_spec_name = f"TDSQL-C {vcpu}C{mem}G"
        ali_spec = info["ali_spec"]
        ali_price = tdsqlc_prices.get(ali_spec, 0)
        tc_price = info["tc_price"]

        if ali_price > 0:
            diff = ali_price - tc_price
            save_pct = (1 - ali_price / tc_price) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"

        print(f"{tc_spec_name:<18} {vcpu:>4} {mem:>6} "
              f"{tc_price:>10.2f} {ali_spec:<28} {ali_price:>10.2f} {diff_str:>8} {save_str:>10}")

    print("\n" + "=" * 150)
    print("说明:")
    print("1. 腾讯云价格为华北地区-北京区域官方定价 (包年包月1个月, Linux)")
    print("   * CVM价格来源: https://buy.cloud.tencent.com/price/cvm/overview")
    print("   * CDB价格为双节点通用型, 不含存储费用")
    print("   * TDSQL-C价格为独享型, 不含存储费用")
    print("2. 阿里云价格为cn-beijing区域实时询价 (包年包月1个月)")
    print("   * ECS价格不含系统盘; RDS/PolarDB不含存储")
    print("3. '阿里云节省%'为正表示阿里云更便宜，为负表示阿里云更贵")
    print("4. 两家均有包年折扣: 包年约85折, 3年约5折")
    print("5. TDSQL-C MySQL ≈ PolarDB MySQL (云原生数据库), 架构类似")
    print("=" * 150)


if __name__ == "__main__":
    main()
