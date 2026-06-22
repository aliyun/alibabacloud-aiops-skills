#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS vs 阿里云 EC2/ECS + 数据库 价格对比脚本"""

import requests
import json
import time

PRICING_URL = "http://localhost:5001/api/pricing/batch"
REGION_ID = "ap-southeast-1"

# ========== AWS EC2 On-Demand Pricing (ap-southeast-1, USD/hr) ==========
AWS_EC2_PRICES = {
    # t3 突发型
    "t3.micro":    {"vcpu": 2, "mem": 1,   "usd_hr": 0.0132, "type": "突发型"},
    "t3.small":    {"vcpu": 2, "mem": 2,   "usd_hr": 0.0264, "type": "突发型"},
    "t3.medium":   {"vcpu": 2, "mem": 4,   "usd_hr": 0.0528, "type": "突发型"},
    "t3.large":    {"vcpu": 2, "mem": 8,   "usd_hr": 0.1056, "type": "突发型"},
    "t3.xlarge":   {"vcpu": 4, "mem": 16,  "usd_hr": 0.2112, "type": "突发型"},
    "t3.2xlarge":  {"vcpu": 8, "mem": 32,  "usd_hr": 0.4224, "type": "突发型"},
    # c5 计算型 (Intel)
    "c5.large":    {"vcpu": 2, "mem": 4,   "usd_hr": 0.0980, "type": "计算型Intel"},
    "c5.xlarge":   {"vcpu": 4, "mem": 8,   "usd_hr": 0.1960, "type": "计算型Intel"},
    "c5.2xlarge":  {"vcpu": 8, "mem": 16,  "usd_hr": 0.3920, "type": "计算型Intel"},
    "c5.4xlarge":  {"vcpu": 16,"mem": 32,  "usd_hr": 0.7840, "type": "计算型Intel"},
    # c6g 计算型 (ARM)
    "c6g.large":   {"vcpu": 2, "mem": 4,   "usd_hr": 0.0784, "type": "计算型ARM"},
    "c6g.xlarge":  {"vcpu": 4, "mem": 8,   "usd_hr": 0.1568, "type": "计算型ARM"},
    "c6g.2xlarge": {"vcpu": 8, "mem": 16,  "usd_hr": 0.3136, "type": "计算型ARM"},
    "c6g.4xlarge": {"vcpu": 16,"mem": 32,  "usd_hr": 0.6272, "type": "计算型ARM"},
    # m5 通用型 (Intel)
    "m5.large":    {"vcpu": 2, "mem": 8,   "usd_hr": 0.1200, "type": "通用型Intel"},
    "m5.xlarge":   {"vcpu": 4, "mem": 16,  "usd_hr": 0.2400, "type": "通用型Intel"},
    "m5.2xlarge":  {"vcpu": 8, "mem": 32,  "usd_hr": 0.4800, "type": "通用型Intel"},
    "m5.4xlarge":  {"vcpu": 16,"mem": 64,  "usd_hr": 0.9600, "type": "通用型Intel"},
    # m6g 通用型 (ARM)
    "m6g.large":   {"vcpu": 2, "mem": 8,   "usd_hr": 0.0960, "type": "通用型ARM"},
    "m6g.xlarge":  {"vcpu": 4, "mem": 16,  "usd_hr": 0.1920, "type": "通用型ARM"},
    "m6g.2xlarge": {"vcpu": 8, "mem": 32,  "usd_hr": 0.3840, "type": "通用型ARM"},
    "m6g.4xlarge": {"vcpu": 16,"mem": 64,  "usd_hr": 0.7680, "type": "通用型ARM"},
    # r5 内存型 (Intel)
    "r5.large":    {"vcpu": 2, "mem": 16,  "usd_hr": 0.1520, "type": "内存型Intel"},
    "r5.xlarge":   {"vcpu": 4, "mem": 32,  "usd_hr": 0.3040, "type": "内存型Intel"},
    "r5.2xlarge":  {"vcpu": 8, "mem": 64,  "usd_hr": 0.6080, "type": "内存型Intel"},
    "r5.4xlarge":  {"vcpu": 16,"mem": 128, "usd_hr": 1.2160, "type": "内存型Intel"},
    # r6g 内存型 (ARM)
    "r6g.large":   {"vcpu": 2, "mem": 16,  "usd_hr": 0.1216, "type": "内存型ARM"},
    "r6g.xlarge":  {"vcpu": 4, "mem": 32,  "usd_hr": 0.2432, "type": "内存型ARM"},
    "r6g.2xlarge": {"vcpu": 8, "mem": 64,  "usd_hr": 0.4864, "type": "内存型ARM"},
    "r6g.4xlarge": {"vcpu": 16,"mem": 128, "usd_hr": 0.9728, "type": "内存型ARM"},
}

# AWS EC2 → 阿里云 ECS 映射
EC2_TO_ECS = {
    "t3.micro":    "ecs.t6-c1m2.large",
    "t3.small":    "ecs.t6-c1m2.large",
    "t3.medium":   "ecs.t6-c1m2.large",
    "t3.large":    "ecs.t6-c1m2.large",
    "t3.xlarge":   "ecs.c8y.xlarge",
    "t3.2xlarge":  "ecs.c8y.2xlarge",
    "c5.large":    "ecs.c7.large",
    "c5.xlarge":   "ecs.c7.xlarge",
    "c5.2xlarge":  "ecs.c7.2xlarge",
    "c5.4xlarge":  "ecs.c7.4xlarge",
    "c6g.large":   "ecs.c8y.large",
    "c6g.xlarge":  "ecs.c8y.xlarge",
    "c6g.2xlarge": "ecs.c8y.2xlarge",
    "c6g.4xlarge": "ecs.c8y.4xlarge",
    "m5.large":    "ecs.g7.large",
    "m5.xlarge":   "ecs.g7.xlarge",
    "m5.2xlarge":  "ecs.g7.2xlarge",
    "m5.4xlarge":  "ecs.g7.4xlarge",
    "m6g.large":   "ecs.g8y.large",
    "m6g.xlarge":  "ecs.g8y.xlarge",
    "m6g.2xlarge": "ecs.g8y.2xlarge",
    "m6g.4xlarge": "ecs.g8y.4xlarge",
    "r5.large":    "ecs.r7.large",
    "r5.xlarge":   "ecs.r7.xlarge",
    "r5.2xlarge":  "ecs.r7.2xlarge",
    "r5.4xlarge":  "ecs.r7.4xlarge",
    "r6g.large":   "ecs.r8y.large",
    "r6g.xlarge":  "ecs.r8y.xlarge",
    "r6g.2xlarge": "ecs.r8y.2xlarge",
    "r6g.4xlarge": "ecs.r8y.4xlarge",
}

# ========== AWS Aurora MySQL On-Demand (ap-southeast-1, USD/hr) ==========
# 基于 AWS Aurora MySQL ap-southeast-1 公开定价
AWS_AURORA_PRICES = {
    "db.t3.micro":    {"vcpu": 2, "mem": 1,   "usd_hr": 0.021,  "type": "突发型Intel"},
    "db.t3.small":    {"vcpu": 2, "mem": 2,   "usd_hr": 0.042,  "type": "突发型Intel"},
    "db.t3.medium":   {"vcpu": 2, "mem": 4,   "usd_hr": 0.084,  "type": "突发型Intel"},
    "db.t3.large":    {"vcpu": 2, "mem": 8,   "usd_hr": 0.168,  "type": "突发型Intel"},
    "db.t4g.micro":   {"vcpu": 2, "mem": 1,   "usd_hr": 0.019,  "type": "突发型ARM"},
    "db.t4g.small":   {"vcpu": 2, "mem": 2,   "usd_hr": 0.038,  "type": "突发型ARM"},
    "db.t4g.medium":  {"vcpu": 2, "mem": 4,   "usd_hr": 0.076,  "type": "突发型ARM"},
    "db.t4g.large":   {"vcpu": 2, "mem": 8,   "usd_hr": 0.150,  "type": "突发型ARM"},
    "db.r5.large":    {"vcpu": 2, "mem": 16,  "usd_hr": 0.290,  "type": "内存型Intel"},
    "db.r5.xlarge":   {"vcpu": 4, "mem": 32,  "usd_hr": 0.580,  "type": "内存型Intel"},
    "db.r5.2xlarge":  {"vcpu": 8, "mem": 64,  "usd_hr": 1.160,  "type": "内存型Intel"},
    "db.r5.4xlarge":  {"vcpu": 16,"mem": 128, "usd_hr": 2.320,  "type": "内存型Intel"},
    "db.r6g.large":   {"vcpu": 2, "mem": 16,  "usd_hr": 0.260,  "type": "内存型ARM"},
    "db.r6g.xlarge":  {"vcpu": 4, "mem": 32,  "usd_hr": 0.520,  "type": "内存型ARM"},
    "db.r6g.2xlarge": {"vcpu": 8, "mem": 64,  "usd_hr": 1.040,  "type": "内存型ARM"},
    "db.r6g.4xlarge": {"vcpu": 16,"mem": 128, "usd_hr": 2.080,  "type": "内存型ARM"},
    "db.m5.large":    {"vcpu": 2, "mem": 8,   "usd_hr": 0.210,  "type": "通用型Intel"},
    "db.m5.xlarge":   {"vcpu": 4, "mem": 16,  "usd_hr": 0.420,  "type": "通用型Intel"},
    "db.m5.2xlarge":  {"vcpu": 8, "mem": 32,  "usd_hr": 0.840,  "type": "通用型Intel"},
    "db.m5.4xlarge":  {"vcpu": 16,"mem": 64,  "usd_hr": 1.680,  "type": "通用型Intel"},
    "db.m6g.large":   {"vcpu": 2, "mem": 8,   "usd_hr": 0.186,  "type": "通用型ARM"},
    "db.m6g.xlarge":  {"vcpu": 4, "mem": 16,  "usd_hr": 0.372,  "type": "通用型ARM"},
    "db.m6g.2xlarge": {"vcpu": 8, "mem": 32,  "usd_hr": 0.744,  "type": "通用型ARM"},
    "db.m6g.4xlarge": {"vcpu": 16,"mem": 64,  "usd_hr": 1.488,  "type": "通用型ARM"},
}

# Aurora/RDS → 阿里云 RDS/PolarDB 映射 (MySQL)
AURORA_TO_ALIYUN = {
    "db.t3.micro":    {"aliyun": "rds.mysql.t1.small",       "product": "rds"},
    "db.t3.small":    {"aliyun": "rds.mysql.s1.small",       "product": "rds"},
    "db.t3.medium":   {"aliyun": "rds.mysql.s2.large",       "product": "rds"},
    "db.t3.large":    {"aliyun": "rds.mysql.s2.xlarge",      "product": "rds"},
    "db.t4g.micro":   {"aliyun": "polar.mysql.g2.medium",    "product": "polardb"},
    "db.t4g.small":   {"aliyun": "polar.mysql.g2.medium",    "product": "polardb"},
    "db.t4g.medium":  {"aliyun": "polar.mysql.g2.large",     "product": "polardb"},
    "db.t4g.large":   {"aliyun": "polar.mysql.g2.xlarge",    "product": "polardb"},
    "db.r5.large":    {"aliyun": "rds.mysql.s2.xlarge",      "product": "rds"},
    "db.r5.xlarge":   {"aliyun": "rds.mysql.s3.large",       "product": "rds"},
    "db.r5.2xlarge":  {"aliyun": "rds.mysql.m1.medium",      "product": "rds"},
    "db.r5.4xlarge":  {"aliyun": "rds.mysql.m1.xlarge",      "product": "rds"},
    "db.r6g.large":   {"aliyun": "polar.mysql.g2.xlarge",    "product": "polardb"},
    "db.r6g.xlarge":  {"aliyun": "polar.mysql.g4.xlarge",    "product": "polardb"},
    "db.r6g.2xlarge": {"aliyun": "polar.mysql.g8.xlarge",    "product": "polardb"},
    "db.r6g.4xlarge": {"aliyun": "polar.mysql.g8.2xlarge",   "product": "polardb"},
    "db.m5.large":    {"aliyun": "rds.mysql.s2.xlarge",      "product": "rds"},
    "db.m5.xlarge":   {"aliyun": "rds.mysql.s3.large",       "product": "rds"},
    "db.m5.2xlarge":  {"aliyun": "rds.mysql.m1.medium",      "product": "rds"},
    "db.m5.4xlarge":  {"aliyun": "rds.mysql.m1.xlarge",      "product": "rds"},
    "db.m6g.large":   {"aliyun": "polar.mysql.g2.xlarge",    "product": "polardb"},
    "db.m6g.xlarge":  {"aliyun": "polar.mysql.g4.xlarge",    "product": "polardb"},
    "db.m6g.2xlarge": {"aliyun": "polar.mysql.g8.xlarge",    "product": "polardb"},
    "db.m6g.4xlarge": {"aliyun": "polar.mysql.g8.2xlarge",   "product": "polardb"},
}

USD_TO_CNY = 7.25  # 汇率

def batch_query_ecs(specs):
    """批量查询ECS价格"""
    items = []
    for spec in specs:
        items.append({
            "product_code": "ecs",
            "instance_spec": spec,
            "region_id": REGION_ID,
            "period": 1,
            "quantity": 1
        })
    results = {}
    # 分批查询，每批5个
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
            print(f"ECS询价批次失败: {e}")
        time.sleep(0.5)
    return results

def batch_query_db(specs_with_product):
    """批量查询数据库价格"""
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
    batch_size = 3
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
            print(f"DB询价批次失败: {e}")
        time.sleep(0.5)
    return results

def main():
    print("=" * 140)
    print("AWS vs 阿里云 价格对比报告 (区域: ap-southeast-1 新加坡)")
    print("=" * 140)
    
    # ===== Part 1: EC2 vs ECS =====
    print("\n" + "=" * 140)
    print("一、EC2 vs ECS 虚拟机价格对比")
    print("=" * 140)
    
    # 收集所有阿里云ECS规格
    ecs_specs = list(set(EC2_TO_ECS.values()))
    print(f"\n正在查询 {len(ecs_specs)} 个阿里云ECS规格的实时价格...")
    
    ecs_prices = batch_query_ecs(ecs_specs)
    
    print(f"成功获取 {len(ecs_prices)} 个ECS规格价格\n")
    
    # 打印EC2对比表头
    header = f"{'AWS EC2规格':<18} {'类型':<12} {'vCPU':>4} {'内存GB':>6} {'AWS月价(USD)':>12} {'AWS月价(CNY)':>12} {'阿里云ECS规格':<24} {'阿里云月价(CNY)':>14} {'价差':>8} {'节省%':>6}"
    print(header)
    print("-" * 140)
    
    # 按类型分组输出
    ec2_types_order = ["突发型", "计算型Intel", "计算型ARM", "通用型Intel", "通用型ARM", "内存型Intel", "内存型ARM"]
    last_type = ""
    
    ec2_items = sorted(AWS_EC2_PRICES.items(), key=lambda x: (ec2_types_order.index(x[1]["type"]), x[1]["vcpu"], x[1]["mem"]))
    
    for ec2_spec, info in ec2_items:
        if info["type"] != last_type:
            if last_type:
                print()
            last_type = info["type"]
        
        aws_monthly_usd = info["usd_hr"] * 730  # 730 hours/month
        aws_monthly_cny = aws_monthly_usd * USD_TO_CNY
        
        aliyun_spec = EC2_TO_ECS.get(ec2_spec, "")
        aliyun_price = ecs_prices.get(aliyun_spec, 0)
        
        if aliyun_price > 0:
            diff = aliyun_price - aws_monthly_cny
            save_pct = (1 - aliyun_price / aws_monthly_cny) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"
        
        print(f"{ec2_spec:<18} {info['type']:<12} {info['vcpu']:>4} {info['mem']:>6} {aws_monthly_usd:>12.2f} {aws_monthly_cny:>12.0f} {aliyun_spec:<24} {aliyun_price:>14.0f} {diff_str:>8} {save_str:>6}")
    
    # ===== Part 2: Aurora/RDS vs RDS/PolarDB =====
    print("\n\n" + "=" * 140)
    print("二、Aurora MySQL vs 阿里云RDS/PolarDB 数据库价格对比")
    print("=" * 140)
    
    # 收集所有阿里云数据库规格
    db_specs = []
    for aws_spec, mapping in AURORA_TO_ALIYUN.items():
        db_specs.append((mapping["aliyun"], mapping["product"]))
    
    # 去重
    unique_db = list(set(db_specs))
    print(f"\n正在查询 {len(unique_db)} 个阿里云数据库规格的实时价格...")
    
    db_prices = batch_query_db(unique_db)
    
    print(f"成功获取 {len(db_prices)} 个数据库规格价格\n")
    
    header = f"{'AWS Aurora规格':<20} {'类型':<12} {'vCPU':>4} {'内存GB':>6} {'AWS月价(USD)':>12} {'AWS月价(CNY)':>12} {'阿里云DB规格':<28} {'产品':>8} {'阿里云月价(CNY)':>14} {'价差':>8} {'节省%':>6}"
    print(header)
    print("-" * 140)
    
    aurora_types_order = ["突发型Intel", "突发型ARM", "通用型Intel", "通用型ARM", "内存型Intel", "内存型ARM"]
    last_type = ""
    
    aurora_items = sorted(AWS_AURORA_PRICES.items(), key=lambda x: (aurora_types_order.index(x[1]["type"]), x[1]["vcpu"], x[1]["mem"]))
    
    for aws_spec, info in aurora_items:
        if info["type"] != last_type:
            if last_type:
                print()
            last_type = info["type"]
        
        aws_monthly_usd = info["usd_hr"] * 730
        aws_monthly_cny = aws_monthly_usd * USD_TO_CNY
        
        mapping = AURORA_TO_ALIYUN.get(aws_spec, {})
        aliyun_spec = mapping.get("aliyun", "")
        product = mapping.get("product", "")
        aliyun_price = db_prices.get(aliyun_spec, 0)
        
        if aliyun_price > 0:
            diff = aliyun_price - aws_monthly_cny
            save_pct = (1 - aliyun_price / aws_monthly_cny) * 100
            diff_str = f"{diff:+.0f}"
            save_str = f"{save_pct:+.1f}%"
        else:
            diff_str = "N/A"
            save_str = "N/A"
        
        product_label = "PolarDB" if product == "polardb" else "RDS"
        print(f"{aws_spec:<20} {info['type']:<12} {info['vcpu']:>4} {info['mem']:>6} {aws_monthly_usd:>12.2f} {aws_monthly_cny:>12.0f} {aliyun_spec:<28} {product_label:>8} {aliyun_price:>14.0f} {diff_str:>8} {save_str:>6}")
    
    print("\n" + "=" * 140)
    print("说明:")
    print("1. AWS价格为 On-Demand 按需定价，ap-southeast-1 (新加坡) 区域，USD/小时 × 730小时/月")
    print("2. 阿里云价格为实时询价（包年包月1个月），ap-southeast-1 (新加坡) 区域，单位：CNY/月")
    print("3. 汇率: 1 USD = 7.25 CNY")
    print("4. 节省%为正表示阿里云更便宜，为负表示阿里云更贵")
    print("5. AWS EC2 不含EBS磁盘费用，阿里云ECS含20GB ESSD系统盘")
    print("6. AWS Aurora 不含存储费用，阿里云RDS含默认存储")
    print("=" * 140)

if __name__ == "__main__":
    main()
