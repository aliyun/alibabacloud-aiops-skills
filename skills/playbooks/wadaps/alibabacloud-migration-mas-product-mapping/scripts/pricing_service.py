#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alibaba Cloud Product Real-time Pricing Service (Python)
Calls Alibaba Cloud DescribePrice OpenAPI for real-time pricing

Start:
    pip install -r requirements.txt
    python pricing_service.py

Default listen: http://0.0.0.0:5000
"""

import hashlib
import hmac
import base64
import json
import uuid
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============ Credential Configuration ============
# Uses Alibaba Cloud default credential provider chain.
# Resolution order: env vars -> OIDC -> ECS RAM Role -> credential file
# See: https://help.aliyun.com/document_detail/378659.html

from alibabacloud_credentials.client import Client as CredClient

_cred_client = None


def _get_cred_client():
    global _cred_client
    if _cred_client is None:
        _cred_client = CredClient()
    return _cred_client


def get_credentials() -> tuple[str, str]:
    """Get AK/SK via Alibaba Cloud default credential provider chain."""
    try:
        cred = _get_cred_client()
        ak = cred.get_access_key_id()
        sk = cred.get_access_key_secret()
        if ak and sk:
            return ak, sk
    except Exception as e:
        app.logger.warning(f"Default credential chain failed: {e}")
    return "", ""


# ============ User-Agent Configuration ============
_SKILL_NAME = "alibabacloud-migration-mas-product-mapping"
_SESSION_ID = os.environ.get("SKILL_SESSION_ID", uuid.uuid4().hex)
_USER_AGENT = f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{_SESSION_ID}"


# ============ Alibaba Cloud OpenAPI Signature V1 ============

def _percent_encode(s: str) -> str:
    return urllib.parse.quote(s, safe="").replace("+", "%20").replace("*", "%2A").replace("%7E", "~")


def call_aliyun_api(endpoint: str, version: str, params: dict) -> dict:
    """
    Call Alibaba Cloud OpenAPI (Signature V1, GET method)
    """
    ak, sk = get_credentials()
    if not ak or not sk:
        return {"error": "Credential chain resolution failed. Ensure the runtime environment provides valid credentials."}

    # Common parameters
    common_params = {
        "Format": "JSON",
        "Version": version,
        "AccessKeyId": ak,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    all_params = {**common_params, **params}

    # Build signature string
    sorted_params = sorted(all_params.items())
    canonicalized = "&".join(f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in sorted_params)
    string_to_sign = f"GET&{_percent_encode('/')}&{_percent_encode(canonicalized)}"

    # HMAC-SHA1 Signature
    sign_key = (sk + "&").encode("utf-8")
    signature = base64.b64encode(
        hmac.new(sign_key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")
    all_params["Signature"] = signature

    # Send request
    url = f"https://{endpoint}/"
    headers = {"User-Agent": _USER_AGENT}
    try:
        resp = requests.get(url, params=all_params, headers=headers, timeout=30)
        return resp.json()
    except requests.RequestException as e:
        return {"error": f"API call failed: {str(e)}"}


# ============ ECS Pricing ============

def query_ecs_price(region_id: str, instance_type: str, period: int = 1,
                    disk_category: str = "cloud_essd", disk_size: int = 40,
                    data_disk_category: str = "", data_disk_size: int = 0,
                    data_disk_pl: str = "PL1") -> dict:
    """ECS instance pricing (subscription), supports system disk + data disk"""
    params = {
        "Action": "DescribePrice",
        "RegionId": region_id,
        "ResourceType": "instance",
        "InstanceType": instance_type,
        "PriceUnit": "Year" if period >= 12 else "Month",
        "Period": str(period // 12 if period >= 12 else period),
        "InstanceNetworkType": "vpc",
        "InternetChargeType": "PayByTraffic",
        "InternetMaxBandwidthOut": "0",
        "SystemDisk.Category": disk_category,
        "SystemDisk.Size": str(disk_size),
    }
    # If data disk exists, add to pricing query
    if data_disk_size > 0:
        dk_cat = data_disk_category or "cloud_essd"
        params["DataDisk.1.Category"] = dk_cat
        params["DataDisk.1.Size"] = str(data_disk_size)
        if dk_cat == "cloud_essd" and data_disk_pl:
            params["DataDisk.1.PerformanceLevel"] = data_disk_pl
    endpoint = f"ecs.{region_id}.aliyuncs.com"
    result = call_aliyun_api(endpoint, "2014-05-26", params)
    return _parse_ecs_price(result, instance_type, region_id)


def query_ecs_payg_price(region_id: str, instance_type: str,
                         disk_category: str = "cloud_essd", disk_size: int = 40) -> dict:
    """ECS pay-as-you-go pricing"""
    params = {
        "Action": "DescribePrice",
        "RegionId": region_id,
        "ResourceType": "instance",
        "InstanceType": instance_type,
        "InstanceNetworkType": "vpc",
        "InternetChargeType": "PayByTraffic",
        "InternetMaxBandwidthOut": "0",
        "SystemDisk.Category": disk_category,
        "SystemDisk.Size": str(disk_size),
    }
    endpoint = f"ecs.{region_id}.aliyuncs.com"
    result = call_aliyun_api(endpoint, "2014-05-26", params)
    return _parse_ecs_price(result, instance_type, region_id)


# ============ RDS Pricing ============

def query_rds_price(region_id: str, engine: str, engine_version: str,
                    db_instance_class: str, storage: int = 100, period: int = 1) -> dict:
    """RDS database pricing"""
    params = {
        "Action": "DescribePrice",
        "RegionId": region_id,
        "Engine": engine,
        "EngineVersion": engine_version,
        "DBInstanceClass": db_instance_class,
        "DBInstanceStorage": str(storage),
        "DBInstanceStorageType": "cloud_essd",
        "PayType": "Prepaid",
        "UsedTime": str(period // 12 if period >= 12 else period),
        "TimeType": "Year" if period >= 12 else "Month",
        "OrderType": "BUY",
        "Quantity": "1",
    }
    result = call_aliyun_api("rds.aliyuncs.com", "2014-08-15", params)
    return _parse_rds_price(result, db_instance_class, region_id)


# ============ Redis pricing ============

def query_redis_price(region_id: str, instance_class: str,
                      capacity: int = 1024, period: int = 1) -> dict:
    """Redis pricing"""
    params = {
        "Action": "DescribePrice",
        "RegionId": region_id,
        "InstanceClass": instance_class,
        "Capacity": str(capacity),
        "NodeType": "MASTER_SLAVE",
        "ChargeType": "PrePaid",
        "Period": str(period),
        "OrderType": "BUY",
        "Quantity": "1",
    }
    result = call_aliyun_api("r-kvstore.aliyuncs.com", "2015-01-01", params)
    return _parse_redis_price(result, instance_class, region_id)


# ============ SLB Pricing (via BSS GetSubscriptionPrice)============

def query_slb_price(region_id: str, spec: str = "slb.s1.small", period: int = 1) -> dict:
    """SLB load balancer pricing (via BSS unified pricing API)"""
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "slb",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "LoadBalancerSpec",
        "ModuleList.1.Config": f"LoadBalancerSpec:{spec}",
        "ModuleList.2.ModuleCode": "InternetTrafficOut",
        "ModuleList.2.Config": "InternetTrafficOut:1",
        "ModuleList.3.ModuleCode": "InstanceRent",
        "ModuleList.3.Config": "InstanceRent:1",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "Quantity": "1",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "SLB", spec, region_id)


# ============ PolarDB Pricing (via BSS GetSubscriptionPrice)============

def query_polardb_price(region_id: str, db_node_class: str, engine: str = "MySQL",
                        storage_space: int = 50, period: int = 1) -> dict:
    """PolarDB pricing - use DescribeClassList API to get ReferencePrice (per-node monthly)"""
    params = {
        "Action": "DescribeClassList",
        "RegionId": region_id,
        "CommodityCode": "polardb_sub",
    }
    result = call_aliyun_api("polardb.aliyuncs.com", "2017-08-01", params)
    items = result.get("Items", [])
    if not items:
        return _error_result("polardb", db_node_class,
                             f"DescribeClassList returned empty: {result.get('Code', '')} {result.get('Message', '')}")

    # Find target spec in spec list
    for it in items:
        if it.get("ClassCode") == db_node_class:
            ref_price_fen = int(it.get("ReferencePrice", "0"))
            monthly_yuan = ref_price_fen / 100.0
            # period Conversion
            total_price = monthly_yuan * period
            return {
                "success": True,
                "product": "PolarDB",
                "instance_spec": db_node_class,
                "region_id": region_id,
                "original_price": total_price,
                "trade_price": total_price,
                "currency": "CNY",
                "period": period,
                "period_unit": "Month",
                "price_detail": f"Per-node monthly price ¥{monthly_yuan:.0f} (ReferencePrice={ref_price_fen}fen)",
            }

    return _error_result("polardb", db_node_class,
                         f"Spec {db_node_class} in {region_id} region not found")


# ============ MongoDB Pricing ============

def query_mongodb_price(region_id: str, db_instance_class: str,
                        db_instance_storage: int = 40, period: int = 1) -> dict:
    """MongoDB pricing - via BSS GetSubscriptionPrice"""
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "dds",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "DBInstanceClass",
        "ModuleList.1.Config": f"DBInstanceClass:{db_instance_class}",
        "ModuleList.2.ModuleCode": "DBInstanceStorage",
        "ModuleList.2.Config": f"DBInstanceStorage:{db_instance_storage}",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "Quantity": "1",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "MongoDB", db_instance_class, region_id)


# ============ NAT Gateway pricing ============

def query_nat_price(region_id: str, spec: str = "Small", period: int = 1) -> dict:
    """NAT Gateway pricing (BSS unified pricing)"""
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "natgw",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "natgw_spec",
        "ModuleList.1.Config": f"natgw_spec:{spec}",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "Quantity": "1",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "NAT", spec, region_id)


# ============ EIP Pricing ============

def query_eip_price(region_id: str, bandwidth: int = 5, period: int = 1) -> dict:
    """EIP pricing (BSS unified pricing)"""
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "eip",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "Bandwidth",
        "ModuleList.1.Config": f"Bandwidth:{bandwidth}",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "Quantity": "1",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "EIP", f"{bandwidth}Mbps", region_id)


# ============ Elasticsearch pricing ============

def query_elasticsearch_price(region_id: str, instance_spec: str = "elasticsearch.sn2ne.large",
                               disk_size: int = 100, period: int = 1) -> dict:
    """Elasticsearch pricing (BSS unified pricing)"""
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "elasticsearch",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "ElasticsearchSpec",
        "ModuleList.1.Config": f"ElasticsearchSpec:{instance_spec}",
        "ModuleList.2.ModuleCode": "ElasticsearchStorage",
        "ModuleList.2.Config": f"ElasticsearchStorage:{disk_size}",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "Quantity": "1",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "Elasticsearch", instance_spec, region_id)


# ============ OSS object storage pricing ============

def query_oss_price(region_id: str, storage_class: str = "Standard",
                   capacity_gb: int = 1000, period: int = 1) -> dict:
    """
    OSS object storage pricing - via BSS GetPayAsYouGoPrice getStandard Storagereal-time unit price，
    thenbyeachstoragetype official price ratio to estimate otherstoragetype price。
    storage_class: Standard / IA / Archive / ColdArchive / DeepColdArchive
    capacity_gb: storagecapacity(GB)
    period: Monthcount
    """
    # OSS storagetype normalization
    storage_class_map = {
        "standard": "Standard",
        "ia": "IA", "infrequentaccess": "IA",
        "archive": "Archive",
        "coldarchive": "ColdArchive", "cold_archive": "ColdArchive",
        "deepcoldarchive": "DeepColdArchive", "deep_cold_archive": "DeepColdArchive",
    }
    sc = storage_class_map.get(storage_class.lower(), storage_class)
    spec_label = f"oss.{sc.lower()}.{capacity_gb}gb"

    # eachstoragetype relative toStandard Storageprice ratio of（based on official pricing）
    # Standard=0.12, IA=0.08, Archive=0.033, ColdArchive=0.015, DeepColdArchive=0.0045
    STORAGE_RATIO = {
        "Standard": 1.0,
        "IA": 0.08 / 0.12,           # 0.6667
        "Archive": 0.033 / 0.12,     # 0.275
        "ColdArchive": 0.015 / 0.12, # 0.125
        "DeepColdArchive": 0.0045 / 0.12,  # 0.0375
    }
    ratio = STORAGE_RATIO.get(sc, 1.0)

    # using BSS GetPayAsYouGoPrice getStandard Storagereal-time unit price（PriceType=Hour）
    params = {
        "Action": "GetPayAsYouGoPrice",
        "ProductCode": "oss",
        "SubscriptionType": "PayAsYouGo",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "Storage",
        "ModuleList.1.Config": f"Storage:Standard,Region:{region_id}",
        "ModuleList.1.PriceType": "Hour",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)

    if result.get("Success") and result.get("Data"):
        module_details = result["Data"].get("ModuleDetails", {}).get("ModuleDetail", [])
        if module_details and isinstance(module_details, list):
            md = module_details[0]
            orig_hourly = md.get("OriginalCost", 0)       # Standard StorageOriginal price/GB/hour
            disc_hourly = md.get("CostAfterDiscount", 0)   # Standard StorageDiscounted price/GB/hour

            if orig_hourly > 0:
                # Standard StorageMonthprice = hourly price × 720 (24h × 30d)
                std_orig_monthly = orig_hourly * 720
                std_disc_monthly = disc_hourly * 720 if disc_hourly > 0 else std_orig_monthly

                # byratio to estimate currentstoragetype unit price
                sc_orig_per_gb = std_orig_monthly * ratio
                sc_disc_per_gb = std_disc_monthly * ratio

                # calculate total price
                total_orig = round(sc_orig_per_gb * capacity_gb * period, 2)
                total_disc = round(sc_disc_per_gb * capacity_gb * period, 2)

                price_source = "real-timeAPI" if sc == "Standard" else "real-timeAPI+ratio estimate"
                return {
                    "success": True,
                    "product_code": "OSS",
                    "instance_spec": spec_label,
                    "region_id": region_id,
                    "original_price": total_orig,
                    "trade_price": total_disc,
                    "discount_price": round(total_orig - total_disc, 2),
                    "currency": "CNY",
                    "count": 1,
                    "total_price": total_orig,
                    "total_trade_price": total_disc,
                    "price_detail": f"{sc}storage {capacity_gb}GB × ¥{sc_disc_per_gb:.4f}/GB/Month × {period}Month ({price_source})",
                    "unit_price_per_gb_month": round(sc_disc_per_gb, 4),
                    "unit_original_price_per_gb_month": round(sc_orig_per_gb, 4),
                }

    # fallback: using Alibaba Cloud official reference unit price
    ref_prices = {
        "Standard": 0.12, "IA": 0.08, "Archive": 0.033,
        "ColdArchive": 0.015, "DeepColdArchive": 0.0045,
    }
    unit_price = ref_prices.get(sc, 0.12)
    monthly_total = round(unit_price * capacity_gb * period, 2)
    return {
        "success": True,
        "product_code": "OSS",
        "instance_spec": spec_label,
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"{sc}storage {capacity_gb}GB × ¥{unit_price}/GB/Month × {period}Month (referenceunit price)",
        "unit_price_per_gb_month": unit_price,
        "is_reference_price": True,
    }


# ============ Block Storage（Cloud Disk）Pricing ============

def query_disk_price(region_id: str, disk_category: str = "cloud_essd",
                    disk_size: int = 100, performance_level: str = "PL1") -> dict:
    """
    Block Storage（Cloud Disk）standalonePricing - using ECS DescribePrice ResourceType=disk
    disk_category: cloud_essd / cloud_essd_entry / cloud_ssd / cloud_efficiency / cloud_auto
    disk_size: disk capacity(GB)
    performance_level: ESSD performance level PL0/PL1/PL2/PL3 (only cloud_essd when valid)
    """
    spec_label = f"{disk_category}.{disk_size}gb"
    if disk_category == "cloud_essd":
        spec_label = f"{disk_category}.{performance_level.lower()}.{disk_size}gb"

    params = {
        "Action": "DescribePrice",
        "RegionId": region_id,
        "ResourceType": "disk",
        "DataDisk.1.Category": disk_category,
        "DataDisk.1.Size": str(disk_size),
    }
    # ESSD only needed PerformanceLevel
    if disk_category == "cloud_essd" and performance_level:
        params["DataDisk.1.PerformanceLevel"] = performance_level

    endpoint = f"ecs.{region_id}.aliyuncs.com"
    result = call_aliyun_api(endpoint, "2014-05-26", params)

    price_info = result.get("PriceInfo", {})
    if price_info:
        price = price_info.get("Price", {})
        hourly_total = price.get("TradePrice", 0)
        hourly_orig = price.get("OriginalPrice", 0)

        if hourly_total > 0 or hourly_orig > 0:
            # API return hourly price，multiply by 730 getMonthprice
            monthly_trade = round(hourly_total * 730, 2)
            monthly_orig = round(hourly_orig * 730, 2)
            per_gb_month = round(monthly_trade / disk_size, 4) if disk_size > 0 else 0

            # disk type friendly name
            category_names = {
                "cloud_essd": f"ESSD {performance_level}",
                "cloud_essd_entry": "ESSD Entry",
                "cloud_ssd": "SSD Cloud Disk",
                "cloud_efficiency": "Ultra Cloud Disk",
                "cloud_auto": "ESSD AutoPL",
            }
            cat_name = category_names.get(disk_category, disk_category)

            return {
                "success": True,
                "product_code": "Disk",
                "instance_spec": spec_label,
                "region_id": region_id,
                "original_price": monthly_orig,
                "trade_price": monthly_trade,
                "discount_price": round(monthly_orig - monthly_trade, 2),
                "currency": "CNY",
                "count": 1,
                "total_price": monthly_orig,
                "total_trade_price": monthly_trade,
                "price_detail": f"{cat_name} {disk_size}GB ¥{per_gb_month}/GB/Month (real-timeAPI)",
                "unit_price_per_gb_month": per_gb_month,
            }

    # fallback reference unit price
    ref_prices = {
        "cloud_essd_PL0": 0.35, "cloud_essd_PL1": 0.50,
        "cloud_essd_PL2": 2.00, "cloud_essd_PL3": 4.00,
        "cloud_essd_entry": 0.24,
        "cloud_ssd": 1.00, "cloud_efficiency": 0.35,
        "cloud_auto": 0.50,
    }
    key = f"{disk_category}_{performance_level}" if disk_category == "cloud_essd" else disk_category
    unit_price = ref_prices.get(key, 0.50)
    monthly_total = round(unit_price * disk_size, 2)
    return {
        "success": True,
        "product_code": "Disk",
        "instance_spec": spec_label,
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"{disk_category} {disk_size}GB ¥{unit_price}/GB/Month (referenceunit price)",
        "unit_price_per_gb_month": unit_price,
        "is_reference_price": True,
    }


# ============ NAS File StoragePricing ============

def query_nas_price(region_id: str, storage_type: str = "Capacity",
                   capacity_gb: int = 500, period: int = 1) -> dict:
    """
    NAS File StoragePricing - NAS isbypay-as-you-go product，calculate via reference unit priceMonthfee
    storage_type: Capacity(Capacity) / Performance(Performance) / Extreme(Ultra) /
                  ExtremeAdvance(Ultra Advanced) / General(General Purpose)
    capacity_gb: storagecapacity(GB)
    period: Monthcount
    """
    storage_type_map = {
        "capacity": "Capacity", "Capacity": "Capacity",
        "performance": "Performance", "Performance": "Performance",
        "extreme": "Extreme", "Ultra": "Extreme",
        "extremeadvance": "ExtremeAdvance", "extreme_advance": "ExtremeAdvance",
        "general": "General", "General Purpose": "General",
    }
    st = storage_type_map.get(storage_type.lower(), storage_type)
    spec_label = f"nas.{st.lower()}.{capacity_gb}gb"

    # NAS official pricing（CNY/GB/Month）
    nas_prices = {
        "Capacity": 0.35,           # Capacity
        "Performance": 1.85,        # Performance
        "Extreme": 1.80,            # Ultrastandard
        "ExtremeAdvance": 0.92,     # Ultra Advanced
        "General": 0.15,            # General Purpose NAS
    }
    unit_price = nas_prices.get(st, 0.35)
    monthly_total = round(unit_price * capacity_gb * period, 2)

    nas_names = {
        "Capacity": "Capacity", "Performance": "Performance",
        "Extreme": "Ultra", "ExtremeAdvance": "Ultra Advanced",
        "General": "General Purpose",
    }
    st_name = nas_names.get(st, st)

    return {
        "success": True,
        "product_code": "NAS",
        "instance_spec": spec_label,
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"NAS {st_name} {capacity_gb}GB × ¥{unit_price}/GB/Month × {period}Month (official pricing)",
        "unit_price_per_gb_month": unit_price,
    }


# ============ AnalyticDB PostgreSQL (GPDB) Pricing ============

def query_gpdb_price(region_id: str, instance_spec: str = "gpdb.group.segsdx1",
                     storage_size: int = 50, period: int = 1) -> dict:
    """AnalyticDB PostgreSQL Pricing（BSS unifiedPricing）"""
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "gpdb",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "ModuleList.1.ModuleCode": "SegNodeClass",
        "ModuleList.1.Config": f"SegNodeClass:{instance_spec}",
        "ModuleList.2.ModuleCode": "SegStorageType",
        "ModuleList.2.Config": f"SegStorageType:{storage_size}",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "Quantity": "1",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "GPDB", instance_spec, region_id)


# ============ Kafka Message QueuePricing ============

def query_kafka_price(region_id: str, spec_type: str = "professional",
                     io_max: int = 20, disk_type: int = 1, disk_size: int = 500,
                     topic_quota: int = 50, partition_num: int = 100,
                     period: int = 1) -> dict:
    """Message Queue Kafka EditionPricing（BSS GetSubscriptionPrice）
    spec_type: professional / normal
    io_max: peak traffic MB/s (20/30/60/90/120)
    disk_type: 0=Ultra Cloud Disk, 1=SSD
    disk_size: disk capacity GB
    topic_quota: Topic countvolume
    partition_num: fenregioncount
    """
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    spec_label = f"Kafka-{spec_type}-{io_max}MB-{disk_size}GB-{topic_quota}topic"
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "alikafka",
        "ProductType": "alikafka_pre",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "Quantity": "1",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "ModuleList.1.ModuleCode": "IoMaxSpec",
        "ModuleList.1.Config": f"SpecType:{spec_type},IoMaxSpec:{io_max},RegionId:{region_id}",
        "ModuleList.2.ModuleCode": "DiskSize",
        "ModuleList.2.Config": f"DiskType:{disk_type},DiskSize:{disk_size},RegionId:{region_id}",
        "ModuleList.3.ModuleCode": "TopicQuota",
        "ModuleList.3.Config": f"PartitionNum:0,TopicQuota:{topic_quota},RegionId:{region_id}",
        "ModuleList.4.ModuleCode": "PartitionNum",
        "ModuleList.4.Config": f"PartitionNum:{partition_num},SpecType:{spec_type},RegionId:{region_id}",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "Kafka", spec_label, region_id)


# ============ RocketMQ Message QueuePricing (reference price) ============

def query_rocketmq_price(region_id: str, spec: str = "2000tps",
                        period: int = 1) -> dict:
    """RocketMQ Pricing - BSS API config complex，using official reference price
    spec: 2000tps / 5000tps / 10000tps / 20000tps
    """
    # Official reference price（PlatinumEditionpackageYearpackageMonth，CNY/Month）
    rocketmq_prices = {
        "2000tps": 1880,
        "5000tps": 2800,
        "10000tps": 5200,
        "20000tps": 9600,
    }
    price = rocketmq_prices.get(spec, 1880)
    monthly_total = round(price * period, 2)
    return {
        "success": True,
        "product_code": "RocketMQ",
        "instance_spec": f"RocketMQ-{spec}",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"RocketMQ PlatinumEdition {spec} ¥{price}/Month × {period}Month (Official reference price)",
    }


# ============ RabbitMQ Message QueuePricing (reference price) ============

def query_rabbitmq_price(region_id: str, spec: str = "professional-1000",
                        period: int = 1) -> dict:
    """RabbitMQ Pricing - using official reference price
    spec: professional-1000 / professional-5000 / enterprise-10000
    """
    rabbitmq_prices = {
        "professional-1000": 700,
        "professional-5000": 2200,
        "enterprise-10000": 5500,
        "enterprise-50000": 15000,
    }
    price = rabbitmq_prices.get(spec, 700)
    monthly_total = round(price * period, 2)
    return {
        "success": True,
        "product_code": "RabbitMQ",
        "instance_spec": f"RabbitMQ-{spec}",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"RabbitMQ {spec} ¥{price}/Month × {period}Month (Official reference price)",
    }


# ============ WAF WebApplication FirewallPricing ============

def query_waf_price(region_id: str, edition: str = "pro_asia",
                   period: int = 1) -> dict:
    """WAF Pricing（BSS GetSubscriptionPrice）
    edition: pro_asia(ProfessionalEdition) / business_asia(EnterpriseEdition) / ultimate_asia(FlagshipEdition)
    """
    edition_map = {
        "pro_asia": "version_pro_asia",
        "business_asia": "version_business_asia",
        "ultimate_asia": "version_ultimate_asia",
        "pro": "version_pro_asia",
        "business": "version_business_asia",
        "ultimate": "version_ultimate_asia",
    }
    package_code = edition_map.get(edition, edition)
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    params = {
        "Action": "GetSubscriptionPrice",
        "ProductCode": "waf",
        "ProductType": "waf",
        "SubscriptionType": "Subscription",
        "OrderType": "NewOrder",
        "Region": region_id,
        "Quantity": "1",
        "ServicePeriodQuantity": period_qty,
        "ServicePeriodUnit": period_unit,
        "ModuleList.1.ModuleCode": "PackageCode",
        "ModuleList.1.Config": f"PackageCode:{package_code}",
    }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "WAF", f"WAF-{edition}", region_id)


# ============ DDoS ProtectionPricing ============

def query_ddos_price(region_id: str, edition: str = "bgp",
                    base_bandwidth: int = 20, ip_count: int = 100,
                    period: int = 1) -> dict:
    """DDoS ProtectionPricing（BSS GetSubscriptionPrice）
    edition: bgp(NativeProtection) / coo(Anti-DDoS)
    """
    period_unit = "Year" if period >= 12 else "Month"
    period_qty = str(period // 12 if period >= 12 else period)
    spec_label = f"DDoS-{edition}-{base_bandwidth}G-{ip_count}IP"

    if edition == "coo":
        params = {
            "Action": "GetSubscriptionPrice",
            "ProductCode": "ddos",
            "ProductType": "ddoscoo",
            "SubscriptionType": "Subscription",
            "OrderType": "NewOrder",
            "Region": region_id,
            "Quantity": "1",
            "ServicePeriodQuantity": period_qty,
            "ServicePeriodUnit": period_unit,
            "ModuleList.1.ModuleCode": "BaseBandwidth",
            "ModuleList.1.Config": f"BaseBandwidth:{base_bandwidth},FunctionVersion:default,Region:{region_id}",
            "ModuleList.2.ModuleCode": "FunctionVersion",
            "ModuleList.2.Config": f"FunctionVersion:default,Region:{region_id}",
        }
    else:  # bgp
        params = {
            "Action": "GetSubscriptionPrice",
            "ProductCode": "ddos",
            "ProductType": "ddosbgp",
            "SubscriptionType": "Subscription",
            "OrderType": "NewOrder",
            "Region": region_id,
            "Quantity": "1",
            "ServicePeriodQuantity": period_qty,
            "ServicePeriodUnit": period_unit,
            "ModuleList.1.ModuleCode": "Type",
            "ModuleList.1.Config": f"Type:1,IpCount:{ip_count},BaseBandwidth:{base_bandwidth},Region:{region_id}",
            "ModuleList.2.ModuleCode": "NormalBandwidth",
            "ModuleList.2.Config": f"NormalBandwidth:100,Type:1,Region:{region_id}",
            "ModuleList.3.ModuleCode": "IpCount",
            "ModuleList.3.Config": f"IpCount:{ip_count},Region:{region_id}",
        }
    result = call_aliyun_api("business.aliyuncs.com", "2017-12-14", params)
    return _parse_bss_price(result, "DDoS", spec_label, region_id)


# ============ VPN GatewayPricing (reference price) ============

def query_vpn_price(region_id: str, spec: str = "5M",
                   period: int = 1) -> dict:
    """VPN GatewayPricing - NoBSSmodule，using official reference price"""
    vpn_prices = {
        "5M": 375, "10M": 680, "20M": 1280, "50M": 2980,
        "100M": 5780, "200M": 10780, "500M": 25780, "1000M": 45780,
    }
    price = vpn_prices.get(spec, 375)
    monthly_total = round(price * period, 2)
    return {
        "success": True,
        "product_code": "VPN",
        "instance_spec": f"VPN-{spec}",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"VPNGateway {spec}bandwidth ¥{price}/Month × {period}Month (Official reference price)",
    }


# ============ CDN Pricing (reference price) ============

def query_cdn_price(region_id: str, bandwidth_mbps: int = 100,
                   period: int = 1) -> dict:
    """CDN Pricing - bypeak bandwidth basedfeereferenceprice"""
    # Tiered billingreference（CNY/Mbps/Month）
    if bandwidth_mbps <= 100:
        unit_price = 25.0
    elif bandwidth_mbps <= 500:
        unit_price = 23.0
    elif bandwidth_mbps <= 5000:
        unit_price = 21.5
    else:
        unit_price = 19.0
    monthly_total = round(unit_price * bandwidth_mbps * period, 2)
    return {
        "success": True,
        "product_code": "CDN",
        "instance_spec": f"CDN-{bandwidth_mbps}Mbps",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"CDN {bandwidth_mbps}Mbps × ¥{unit_price}/Mbps/Month × {period}Month (Official reference price)",
    }


# ============ EMR Pricing (reference price) ============

def query_emr_price(region_id: str, spec: str = "emr.c6.2xlarge",
                   node_count: int = 3, period: int = 1) -> dict:
    """EMR Pricing - BSSNo module，based onECSnodepricespec+EMRManagement feeestimate"""
    # EMR Management feereferenceprice（CNY/node/Month）
    emr_mgmt_prices = {
        "emr.c6.xlarge": 120, "emr.c6.2xlarge": 240, "emr.c6.4xlarge": 480,
        "emr.g6.xlarge": 150, "emr.g6.2xlarge": 300, "emr.g6.4xlarge": 600,
        "emr.r6.xlarge": 180, "emr.r6.2xlarge": 360, "emr.r6.4xlarge": 720,
    }
    mgmt_per_node = emr_mgmt_prices.get(spec, 240)
    monthly_total = round(mgmt_per_node * node_count * period, 2)
    return {
        "success": True,
        "product_code": "EMR",
        "instance_spec": f"EMR-{spec}-{node_count}nodes",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"EMRManagement fee {spec} × {node_count}node × ¥{mgmt_per_node}/node/Month × {period}Month (excludingECSunderlyingfeeusage，Official reference price)",
    }


# ============ Flink Realtime ComputePricing (reference price) ============

def query_flink_price(region_id: str, cu_count: int = 2,
                     period: int = 1) -> dict:
    """Flink Realtime ComputePricing - byCUreferenceprice"""
    # fully managedFlink: approx. 0.46CNY/CU/hour ≈ 335.8CNY/CU/Month
    cu_price_monthly = 335.8
    monthly_total = round(cu_price_monthly * cu_count * period, 2)
    return {
        "success": True,
        "product_code": "Flink",
        "instance_spec": f"Flink-{cu_count}CU",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"Flinkfully managed {cu_count}CU × ¥{cu_price_monthly}/CU/Month × {period}Month (Official reference price)",
    }


# ============ SLS Log ServicePricing (reference price) ============

def query_sls_price(region_id: str, ingest_gb_day: int = 10,
                   retention_days: int = 30, period: int = 1) -> dict:
    """SLS Log ServicePricing - bywritevolumeandstoragereferenceprice"""
    # write: 0.2CNY/GB, index: 0.35CNY/GB(enabled by default), storage: 0.0115CNY/GB/day
    daily_ingest_cost = ingest_gb_day * (0.2 + 0.35)
    daily_storage_cost = ingest_gb_day * retention_days * 0.3 * 0.0115  # compression ratioapprox.30%
    monthly_total = round((daily_ingest_cost * 30 + daily_storage_cost * 30) * period, 2)
    return {
        "success": True,
        "product_code": "SLS",
        "instance_spec": f"SLS-{ingest_gb_day}GB/day-{retention_days}d",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"SLS {ingest_gb_day}GB/day write × {retention_days}day retention × {period}Month (Official reference price)",
    }


# ============ MaxCompute Pricing (reference price) ============

def query_maxcompute_price(region_id: str, cu_count: int = 50,
                          storage_tb: int = 1, period: int = 1) -> dict:
    """MaxCompute Pricing - packageYearpackageMonthCU+storagereferenceprice"""
    # packageYearpackageMonth: approx.130CNY/CU/Month(Standard Edition), storage: 0.0192CNY/GB/day
    cu_price = 130.0
    storage_monthly = storage_tb * 1024 * 0.0192 * 30  # GB * CNY/GB/day * 30day
    monthly_total = round((cu_price * cu_count + storage_monthly) * period, 2)
    return {
        "success": True,
        "product_code": "MaxCompute",
        "instance_spec": f"MaxCompute-{cu_count}CU-{storage_tb}TB",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"MaxCompute {cu_count}CU × ¥{cu_price}/CU/Month + {storage_tb}TBstorage × {period}Month (Official reference price)",
    }


# ============ ACK pricing（referenceprice） ============

def query_ack_price(region_id: str, edition: str = "pro",
                   worker_count: int = 3, period: int = 1) -> dict:
    """ACK container service pricing - management fee (excluding Worker node ECS)"""
    ack_prices = {
        "standard": 0,       # Standard edition free
        "pro": 550,          # Professional managed cluster
        "serverless": 380,   # Serverlesscluster
    }
    mgmt_price = ack_prices.get(edition, 550)
    monthly_total = round(mgmt_price * period, 2)
    return {
        "success": True,
        "product_code": "ACK",
        "instance_spec": f"ACK-{edition}-{worker_count}workers",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"ACK {edition}EditionManagement fee ¥{mgmt_price}/Month × {period}Month (excludingWorkernodeECSfeeusage，Official reference price)",
    }


# ============ ECI Elastic Container InstancePricing (reference price) ============

def query_eci_price(region_id: str, cpu: float = 2.0, memory_gb: float = 4.0,
                   hours_per_month: int = 730, period: int = 1) -> dict:
    """ECI Elastic Container InstancePricing - Pay-as-you-go reference price"""
    # vCPU: 0.000127CNY/sec ≈ 0.4572CNY/hour, memory: 0.0000635CNY/GB/sec ≈ 0.2286CNY/GB/hour
    hourly_cost = cpu * 0.4572 + memory_gb * 0.2286
    monthly_total = round(hourly_cost * hours_per_month * period, 2)
    return {
        "success": True,
        "product_code": "ECI",
        "instance_spec": f"ECI-{cpu}C{memory_gb}G",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"ECI {cpu}vCPU/{memory_gb}GB × {hours_per_month}h/Month × {period}Month (Pay-as-you-go reference price)",
    }


# ============ FC Function ComputePricing (reference price) ============

def query_fc_price(region_id: str, memory_mb: int = 512,
                  invocations_million: int = 1,
                  duration_seconds: float = 0.5, period: int = 1) -> dict:
    """Function ComputeFCPricing - Pay-as-you-go reference price"""
    # invocationsusagetimescount: 1.33CNY/hundred10Ktimes, vCPU: 0.00011108CNY/sec, memory: 0.00001388CNY/GB/sec
    cpu_count = memory_mb / 1024.0  # approx.vCPUto memory ratio
    invocations_cost = invocations_million * 1.33
    duration_cost = (cpu_count * 0.00011108 + (memory_mb / 1024.0) * 0.00001388) * duration_seconds * invocations_million * 1000000
    monthly_total = round((invocations_cost + duration_cost) * period, 2)
    return {
        "success": True,
        "product_code": "FC",
        "instance_spec": f"FC-{memory_mb}MB-{invocations_million}M-calls",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"FC {memory_mb}MB × {invocations_million}Minvocationsusage/Month × {duration_seconds}s × {period}Month (Pay-as-you-go reference price)",
    }


# ============ SAE Application EnginePricing (reference price) ============

def query_sae_price(region_id: str, cpu: float = 1.0, memory_gb: float = 2.0,
                   instances: int = 2, period: int = 1) -> dict:
    """SAE ServerlessApplication EnginePricing - Pay-as-you-go reference price"""
    # vCPU: 0.000127CNY/sec ≈ 0.336CNY/hour, memory: 0.042CNY/GB/hour
    hourly_cost = cpu * 0.336 + memory_gb * 0.042
    monthly_total = round(hourly_cost * 730 * instances * period, 2)
    return {
        "success": True,
        "product_code": "SAE",
        "instance_spec": f"SAE-{cpu}C{memory_gb}G-{instances}inst",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"SAE {cpu}vCPU/{memory_gb}GB × {instances}instance × 730h/Month × {period}Month (Pay-as-you-go reference price)",
    }


# ============ Lindorm Multi-model DatabasePricing (reference price) ============

def query_lindorm_price(region_id: str, spec: str = "lindorm.c.xlarge",
                       node_count: int = 2, storage_gb: int = 480,
                       period: int = 1) -> dict:
    """Lindorm pricing - BSS config complex, using official reference price"""
    lindorm_prices = {
        "lindorm.c.xlarge": 1860,    # 4C16G
        "lindorm.c.2xlarge": 3500,   # 8C32G
        "lindorm.c.4xlarge": 6780,   # 16C64G
        "lindorm.c.8xlarge": 13300,  # 32C128G
        "lindorm.g.xlarge": 2100,
        "lindorm.g.2xlarge": 3980,
    }
    node_price = lindorm_prices.get(spec, 1860)
    # Storage fee: Ultra cloud disk approx.0.35CNY/GB/Month
    storage_cost = storage_gb * 0.35
    monthly_total = round((node_price * node_count + storage_cost) * period, 2)
    return {
        "success": True,
        "product_code": "Lindorm",
        "instance_spec": f"Lindorm-{spec}-{node_count}nodes-{storage_gb}GB",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"Lindorm {spec} × {node_count}node + {storage_gb}GBstorage × {period}Month (Official reference price)",
    }


# ============ GDB pricing（referenceprice） ============

def query_gdb_price(region_id: str, spec: str = "gdb.r.2xlarge",
                   storage_gb: int = 50, period: int = 1) -> dict:
    """GDB graph database pricing - using official reference price"""
    gdb_prices = {
        "gdb.r.xlarge": 2370,     # 4C32G
        "gdb.r.2xlarge": 4530,    # 8C64G
        "gdb.r.4xlarge": 8850,    # 16C128G
        "gdb.r.8xlarge": 17490,   # 32C256G
    }
    node_price = gdb_prices.get(spec, 4530)
    storage_cost = storage_gb * 1.0  # approx.1CNY/GB/Month
    monthly_total = round((node_price + storage_cost) * period, 2)
    return {
        "success": True,
        "product_code": "GDB",
        "instance_spec": f"GDB-{spec}-{storage_gb}GB",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"GDB {spec} + {storage_gb}GBstorage × {period}Month (Official reference price)",
    }


# ============ Tablestore Pricing (reference price) ============

def query_tablestore_price(region_id: str, storage_gb: int = 100,
                          read_cu: int = 100, write_cu: int = 50,
                          period: int = 1) -> dict:
    """Tablestore pricing - pay-as-you-go reference price"""
    # storage: 0.0078CNY/GB/hour, readCU: 0.0088CNY/10KCU, writeCU: 0.0176CNY/10KCU
    storage_monthly = storage_gb * 0.0078 * 730  # CNY/GB/h * 730h/Month
    read_monthly = read_cu * 0.0088 * 3600 * 730 / 10000  # CU/sec -> Month
    write_monthly = write_cu * 0.0176 * 3600 * 730 / 10000
    monthly_total = round((storage_monthly + read_monthly + write_monthly) * period, 2)
    return {
        "success": True,
        "product_code": "Tablestore",
        "instance_spec": f"Tablestore-{storage_gb}GB-R{read_cu}-W{write_cu}",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"Tablestore {storage_gb}GB + R{read_cu}CU/s + W{write_cu}CU/s × {period}Month (Pay-as-you-go reference price)",
    }


# ============ HBR backup pricing（referenceprice） ============

def query_hbr_price(region_id: str, storage_gb: int = 500,
                   period: int = 1) -> dict:
    """HBR cloud backup pricing - pay-as-you-go reference price"""
    # Backup storage: 0.1CNY/GB/Month
    monthly_total = round(0.1 * storage_gb * period, 2)
    return {
        "success": True,
        "product_code": "HBR",
        "instance_spec": f"HBR-{storage_gb}GB",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"HBR {storage_gb}GB × ¥0.1/GB/Month × {period}Month (Official reference price)",
    }


# ============ Bastion HostPricing (reference price) ============

def query_bastionhost_price(region_id: str, edition: str = "basic",
                           period: int = 1) -> dict:
    """Bastion Host pricing - using official reference price"""
    bastionhost_prices = {
        "basic": 900,        # Basic Edition(50assets)
        "standard": 3800,    # Standard Edition(200assets)
        "advanced": 11000,   # Advanced Edition(500assets)
    }
    price = bastionhost_prices.get(edition, 900)
    monthly_total = round(price * period, 2)
    return {
        "success": True,
        "product_code": "BastionHost",
        "instance_spec": f"BastionHost-{edition}",
        "region_id": region_id,
        "original_price": monthly_total,
        "trade_price": monthly_total,
        "discount_price": 0,
        "currency": "CNY",
        "count": 1,
        "total_price": monthly_total,
        "total_trade_price": monthly_total,
        "price_detail": f"Bastion Host {edition}Edition ¥{price}/Month × {period}Month (Official reference price)",
    }


# ============ Parsing Logic ============

def _parse_bss_price(resp: dict, product: str, spec: str, region_id: str) -> dict:
    """Parse BSS GetSubscriptionPrice response result"""
    if "error" in resp:
        return _error_result(product, spec, resp["error"])
    if not resp.get("Success", False):
        msg = resp.get("Message", resp.get("Code", "Unknown error"))
        return _error_result(product, spec, msg)
    data = resp.get("Data", {})
    if not data:
        return _error_result(product, spec, "Response data is empty")
    return {
        "success": True,
        "product_code": product,
        "instance_spec": spec,
        "region_id": region_id,
        "original_price": data.get("OriginalPrice", 0),
        "trade_price": data.get("TradePrice", 0),
        "discount_price": data.get("DiscountPrice", 0),
        "currency": data.get("Currency", "CNY"),
        "count": 1,
        "total_price": data.get("OriginalPrice", 0),
        "total_trade_price": data.get("TradePrice", 0),
    }


def _parse_ecs_price(resp: dict, spec: str, region_id: str) -> dict:
    if "error" in resp:
        return _error_result("ECS", spec, resp["error"])
    price_info = resp.get("PriceInfo", {})
    if not price_info:
        msg = resp.get("Message", resp.get("Code", "Unknown error"))
        return _error_result("ECS", spec, msg)
    price = price_info.get("Price", {})
    return {
        "success": True,
        "product_code": "ECS",
        "instance_spec": spec,
        "region_id": region_id,
        "original_price": price.get("OriginalPrice", 0),
        "trade_price": price.get("TradePrice", 0),
        "discount_price": price.get("DiscountPrice", 0),
        "currency": price.get("Currency", "CNY"),
        "count": 1,
        "total_price": price.get("OriginalPrice", 0),
        "total_trade_price": price.get("TradePrice", 0),
    }


def _parse_rds_price(resp: dict, spec: str, region_id: str) -> dict:
    if "error" in resp:
        return _error_result("RDS", spec, resp["error"])
    price_info = resp.get("PriceInfo", {})
    if not price_info:
        msg = resp.get("Message", resp.get("Code", "Unknown error"))
        return _error_result("RDS", spec, msg)
    return {
        "success": True,
        "product_code": "RDS",
        "instance_spec": spec,
        "region_id": region_id,
        "original_price": price_info.get("OriginalPrice", 0),
        "trade_price": price_info.get("TradePrice", 0),
        "discount_price": price_info.get("DiscountPrice", 0),
        "currency": price_info.get("Currency", "CNY"),
        "count": 1,
        "total_price": price_info.get("OriginalPrice", 0),
        "total_trade_price": price_info.get("TradePrice", 0),
    }


def _parse_redis_price(resp: dict, spec: str, region_id: str) -> dict:
    if "error" in resp:
        return _error_result("Redis", spec, resp["error"])
    order = resp.get("Order", {})
    if not order:
        msg = resp.get("Message", resp.get("Code", "Unknown error"))
        return _error_result("Redis", spec, msg)
    return {
        "success": True,
        "product_code": "Redis",
        "instance_spec": spec,
        "region_id": region_id,
        "original_price": order.get("OriginalAmount", 0),
        "trade_price": order.get("TradeAmount", 0),
        "discount_price": order.get("DiscountAmount", 0),
        "currency": order.get("Currency", "CNY"),
        "count": 1,
        "total_price": order.get("OriginalAmount", 0),
        "total_trade_price": order.get("TradeAmount", 0),
    }


def _parse_generic_price(resp: dict, product: str, spec: str, region_id: str) -> dict:
    if "error" in resp:
        return _error_result(product, spec, resp["error"])
    # Try multiple response structures
    price_node = resp.get("PriceInfo", {}).get("Price") or resp.get("Order") or resp.get("PriceInfo")
    if not price_node:
        msg = resp.get("Message", resp.get("Code", "Unknown error"))
        return _error_result(product, spec, msg)
    orig = price_node.get("OriginalPrice", price_node.get("OriginalAmount", 0))
    trade = price_node.get("TradePrice", price_node.get("TradeAmount", 0))
    discount = price_node.get("DiscountPrice", price_node.get("DiscountAmount", 0))
    return {
        "success": True,
        "product_code": product,
        "instance_spec": spec,
        "region_id": region_id,
        "original_price": orig,
        "trade_price": trade,
        "discount_price": discount,
        "currency": "CNY",
        "count": 1,
        "total_price": orig,
        "total_trade_price": trade,
    }


def _error_result(product: str, spec: str, msg: str) -> dict:
    return {
        "success": False,
        "product_code": product,
        "instance_spec": spec,
        "error_message": msg,
    }


# ============ Batch Pricing ============

def batch_query(items: list, default_region: str = "cn-beijing", default_period: int = 1) -> list:
    """Batch Pricing"""
    results = []
    for item in items:
        product_code = item.get("product_code", "").lower()
        spec = item.get("instance_spec", "")
        region = item.get("region_id") or default_region
        period = item.get("period") or default_period
        count = item.get("count", 1)

        if product_code == "ecs":
            r = query_ecs_price(
                region, spec, period,
                item.get("disk_category", "cloud_essd"),
                item.get("disk_size", 40),
                item.get("data_disk_category", ""),
                item.get("data_disk_size", 0),
                item.get("data_disk_pl", "PL1"),
            )
        elif product_code == "rds":
            r = query_rds_price(
                region,
                item.get("engine", "MySQL"),
                item.get("engine_version", "8.0"),
                spec,
                item.get("disk_size", 100),
                period,
            )
        elif product_code == "redis":
            r = query_redis_price(
                region, spec,
                item.get("capacity", 1024),
                period,
            )
        elif product_code == "slb":
            r = query_slb_price(region, spec, period)
        elif product_code == "polardb":
            r = query_polardb_price(
                region, spec,
                item.get("engine", "MySQL"),
                item.get("storage_space", 50),
                period,
            )
        elif product_code == "mongodb":
            r = query_mongodb_price(
                region, spec,
                item.get("disk_size", 20),
                period,
            )
        elif product_code == "nat":
            r = query_nat_price(region, spec, period)
        elif product_code == "eip":
            bandwidth = item.get("bandwidth", 5)
            r = query_eip_price(region, bandwidth, period)
        elif product_code == "elasticsearch":
            r = query_elasticsearch_price(
                region, spec,
                item.get("disk_size", 100),
                period,
            )
        elif product_code == "gpdb":
            r = query_gpdb_price(
                region, spec,
                item.get("storage_size", 50),
                period,
            )
        elif product_code == "oss":
            r = query_oss_price(
                region,
                item.get("storage_class", "Standard"),
                item.get("capacity_gb", 1000),
                period,
            )
        elif product_code == "disk":
            r = query_disk_price(
                region,
                item.get("disk_category", "cloud_essd"),
                item.get("disk_size", 100),
                item.get("performance_level", "PL1"),
            )
        elif product_code == "nas":
            r = query_nas_price(
                region,
                item.get("storage_type", "Capacity"),
                item.get("capacity_gb", 500),
                period,
            )
        elif product_code == "kafka":
            r = query_kafka_price(
                region, item.get("spec_type", "professional"),
                item.get("io_max", 20), item.get("disk_type", 1),
                item.get("disk_size", 500), item.get("topic_quota", 50),
                item.get("partition_num", 100), period,
            )
        elif product_code == "rocketmq":
            r = query_rocketmq_price(region, item.get("spec", "2000tps"), period)
        elif product_code == "rabbitmq":
            r = query_rabbitmq_price(region, item.get("spec", "professional-1000"), period)
        elif product_code == "waf":
            r = query_waf_price(region, item.get("edition", "pro_asia"), period)
        elif product_code == "ddos":
            r = query_ddos_price(
                region, item.get("edition", "bgp"),
                item.get("base_bandwidth", 20), item.get("ip_count", 100), period,
            )
        elif product_code == "vpn":
            r = query_vpn_price(region, item.get("spec", "5M"), period)
        elif product_code == "cdn":
            r = query_cdn_price(region, item.get("bandwidth_mbps", 100), period)
        elif product_code == "emr":
            r = query_emr_price(
                region, item.get("spec", "emr.c6.2xlarge"),
                item.get("node_count", 3), period,
            )
        elif product_code == "flink":
            r = query_flink_price(region, item.get("cu_count", 2), period)
        elif product_code == "sls":
            r = query_sls_price(
                region, item.get("ingest_gb_day", 10),
                item.get("retention_days", 30), period,
            )
        elif product_code == "maxcompute":
            r = query_maxcompute_price(
                region, item.get("cu_count", 50),
                item.get("storage_tb", 1), period,
            )
        elif product_code == "ack":
            r = query_ack_price(
                region, item.get("edition", "pro"),
                item.get("worker_count", 3), period,
            )
        elif product_code == "eci":
            r = query_eci_price(
                region, item.get("cpu", 2.0), item.get("memory_gb", 4.0),
                item.get("hours_per_month", 730), period,
            )
        elif product_code == "fc":
            r = query_fc_price(
                region, item.get("memory_mb", 512),
                item.get("invocations_million", 1),
                item.get("duration_seconds", 0.5), period,
            )
        elif product_code == "sae":
            r = query_sae_price(
                region, item.get("cpu", 1.0), item.get("memory_gb", 2.0),
                item.get("instances", 2), period,
            )
        elif product_code == "lindorm":
            r = query_lindorm_price(
                region, item.get("spec", "lindorm.c.xlarge"),
                item.get("node_count", 2), item.get("storage_gb", 480), period,
            )
        elif product_code == "gdb":
            r = query_gdb_price(
                region, item.get("spec", "gdb.r.2xlarge"),
                item.get("storage_gb", 50), period,
            )
        elif product_code == "tablestore":
            r = query_tablestore_price(
                region, item.get("storage_gb", 100),
                item.get("read_cu", 100), item.get("write_cu", 50), period,
            )
        elif product_code == "hbr":
            r = query_hbr_price(region, item.get("storage_gb", 500), period)
        elif product_code == "bastionhost":
            r = query_bastionhost_price(region, item.get("edition", "basic"), period)
        else:
            r = _error_result(product_code, spec, "This product pricing is not supported, please check Alibaba Cloud official website")

        # Quantity multiplication
        if count > 1 and r.get("success"):
            r["count"] = count
            r["total_price"] = r["original_price"] * count
            r["total_trade_price"] = r["trade_price"] * count

        results.append(r)
    return results


# ============ Flask Routes ============

@app.route("/api/pricing/ecs", methods=["GET"])
def api_ecs_price():
    region_id = request.args.get("region_id", "cn-beijing")
    instance_type = request.args.get("instance_type", "")
    period = int(request.args.get("period", 1))
    disk_category = request.args.get("disk_category", "cloud_essd")
    disk_size = int(request.args.get("disk_size", 40))
    if not instance_type:
        return jsonify({"success": False, "message": "Missing instance_type parameter"})
    result = query_ecs_price(region_id, instance_type, period, disk_category, disk_size)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/ecs/payg", methods=["GET"])
def api_ecs_payg_price():
    region_id = request.args.get("region_id", "cn-beijing")
    instance_type = request.args.get("instance_type", "")
    disk_category = request.args.get("disk_category", "cloud_essd")
    disk_size = int(request.args.get("disk_size", 40))
    if not instance_type:
        return jsonify({"success": False, "message": "Missing instance_type parameter"})
    result = query_ecs_payg_price(region_id, instance_type, disk_category, disk_size)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/rds", methods=["GET"])
def api_rds_price():
    region_id = request.args.get("region_id", "cn-beijing")
    engine = request.args.get("engine", "MySQL")
    engine_version = request.args.get("engine_version", "8.0")
    db_instance_class = request.args.get("db_instance_class", "")
    storage = int(request.args.get("storage", 100))
    period = int(request.args.get("period", 1))
    if not db_instance_class:
        return jsonify({"success": False, "message": "Missing db_instance_class parameter"})
    result = query_rds_price(region_id, engine, engine_version, db_instance_class, storage, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/redis", methods=["GET"])
def api_redis_price():
    region_id = request.args.get("region_id", "cn-beijing")
    instance_class = request.args.get("instance_class", "")
    capacity = int(request.args.get("capacity", 1024))
    period = int(request.args.get("period", 1))
    if not instance_class:
        return jsonify({"success": False, "message": "Missing instance_class parameter"})
    result = query_redis_price(region_id, instance_class, capacity, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/slb", methods=["GET"])
def api_slb_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "slb.s1.small")
    period = int(request.args.get("period", 1))
    result = query_slb_price(region_id, spec, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/disk", methods=["GET"])
def api_disk_price():
    region_id = request.args.get("region_id", "cn-beijing")
    disk_category = request.args.get("disk_category", "cloud_essd")
    disk_size = int(request.args.get("disk_size", 100))
    performance_level = request.args.get("performance_level", "PL1")
    result = query_disk_price(region_id, disk_category, disk_size, performance_level)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/nas", methods=["GET"])
def api_nas_price():
    region_id = request.args.get("region_id", "cn-beijing")
    storage_type = request.args.get("storage_type", "Capacity")
    capacity_gb = int(request.args.get("capacity_gb", 500))
    period = int(request.args.get("period", 1))
    result = query_nas_price(region_id, storage_type, capacity_gb, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/oss", methods=["GET"])
def api_oss_price():
    region_id = request.args.get("region_id", "cn-beijing")
    storage_class = request.args.get("storage_class", "Standard")
    capacity_gb = int(request.args.get("capacity_gb", 1000))
    period = int(request.args.get("period", 1))
    result = query_oss_price(region_id, storage_class, capacity_gb, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/kafka", methods=["GET"])
def api_kafka_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec_type = request.args.get("spec_type", "professional")
    io_max = int(request.args.get("io_max", 20))
    disk_type = int(request.args.get("disk_type", 1))
    disk_size = int(request.args.get("disk_size", 500))
    topic_quota = int(request.args.get("topic_quota", 50))
    partition_num = int(request.args.get("partition_num", 100))
    period = int(request.args.get("period", 1))
    result = query_kafka_price(region_id, spec_type, io_max, disk_type, disk_size, topic_quota, partition_num, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/rocketmq", methods=["GET"])
def api_rocketmq_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "2000tps")
    period = int(request.args.get("period", 1))
    result = query_rocketmq_price(region_id, spec, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/rabbitmq", methods=["GET"])
def api_rabbitmq_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "professional-1000")
    period = int(request.args.get("period", 1))
    result = query_rabbitmq_price(region_id, spec, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/waf", methods=["GET"])
def api_waf_price():
    region_id = request.args.get("region_id", "cn-beijing")
    edition = request.args.get("edition", "pro_asia")
    period = int(request.args.get("period", 1))
    result = query_waf_price(region_id, edition, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/ddos", methods=["GET"])
def api_ddos_price():
    region_id = request.args.get("region_id", "cn-beijing")
    edition = request.args.get("edition", "bgp")
    base_bandwidth = int(request.args.get("base_bandwidth", 20))
    ip_count = int(request.args.get("ip_count", 100))
    period = int(request.args.get("period", 1))
    result = query_ddos_price(region_id, edition, base_bandwidth, ip_count, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/vpn", methods=["GET"])
def api_vpn_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "5M")
    period = int(request.args.get("period", 1))
    result = query_vpn_price(region_id, spec, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/cdn", methods=["GET"])
def api_cdn_price():
    region_id = request.args.get("region_id", "cn-beijing")
    bandwidth_mbps = int(request.args.get("bandwidth_mbps", 100))
    period = int(request.args.get("period", 1))
    result = query_cdn_price(region_id, bandwidth_mbps, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/emr", methods=["GET"])
def api_emr_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "emr.c6.2xlarge")
    node_count = int(request.args.get("node_count", 3))
    period = int(request.args.get("period", 1))
    result = query_emr_price(region_id, spec, node_count, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/flink", methods=["GET"])
def api_flink_price():
    region_id = request.args.get("region_id", "cn-beijing")
    cu_count = int(request.args.get("cu_count", 2))
    period = int(request.args.get("period", 1))
    result = query_flink_price(region_id, cu_count, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/sls", methods=["GET"])
def api_sls_price():
    region_id = request.args.get("region_id", "cn-beijing")
    ingest_gb_day = int(request.args.get("ingest_gb_day", 10))
    retention_days = int(request.args.get("retention_days", 30))
    period = int(request.args.get("period", 1))
    result = query_sls_price(region_id, ingest_gb_day, retention_days, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/maxcompute", methods=["GET"])
def api_maxcompute_price():
    region_id = request.args.get("region_id", "cn-beijing")
    cu_count = int(request.args.get("cu_count", 50))
    storage_tb = int(request.args.get("storage_tb", 1))
    period = int(request.args.get("period", 1))
    result = query_maxcompute_price(region_id, cu_count, storage_tb, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/ack", methods=["GET"])
def api_ack_price():
    region_id = request.args.get("region_id", "cn-beijing")
    edition = request.args.get("edition", "pro")
    worker_count = int(request.args.get("worker_count", 3))
    period = int(request.args.get("period", 1))
    result = query_ack_price(region_id, edition, worker_count, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/eci", methods=["GET"])
def api_eci_price():
    region_id = request.args.get("region_id", "cn-beijing")
    cpu = float(request.args.get("cpu", 2.0))
    memory_gb = float(request.args.get("memory_gb", 4.0))
    hours_per_month = int(request.args.get("hours_per_month", 730))
    period = int(request.args.get("period", 1))
    result = query_eci_price(region_id, cpu, memory_gb, hours_per_month, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/fc", methods=["GET"])
def api_fc_price():
    region_id = request.args.get("region_id", "cn-beijing")
    memory_mb = int(request.args.get("memory_mb", 512))
    invocations_million = int(request.args.get("invocations_million", 1))
    duration_seconds = float(request.args.get("duration_seconds", 0.5))
    period = int(request.args.get("period", 1))
    result = query_fc_price(region_id, memory_mb, invocations_million, duration_seconds, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/sae", methods=["GET"])
def api_sae_price():
    region_id = request.args.get("region_id", "cn-beijing")
    cpu = float(request.args.get("cpu", 1.0))
    memory_gb = float(request.args.get("memory_gb", 2.0))
    instances = int(request.args.get("instances", 2))
    period = int(request.args.get("period", 1))
    result = query_sae_price(region_id, cpu, memory_gb, instances, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/lindorm", methods=["GET"])
def api_lindorm_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "lindorm.c.xlarge")
    node_count = int(request.args.get("node_count", 2))
    storage_gb = int(request.args.get("storage_gb", 480))
    period = int(request.args.get("period", 1))
    result = query_lindorm_price(region_id, spec, node_count, storage_gb, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/gdb", methods=["GET"])
def api_gdb_price():
    region_id = request.args.get("region_id", "cn-beijing")
    spec = request.args.get("spec", "gdb.r.2xlarge")
    storage_gb = int(request.args.get("storage_gb", 50))
    period = int(request.args.get("period", 1))
    result = query_gdb_price(region_id, spec, storage_gb, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/tablestore", methods=["GET"])
def api_tablestore_price():
    region_id = request.args.get("region_id", "cn-beijing")
    storage_gb = int(request.args.get("storage_gb", 100))
    read_cu = int(request.args.get("read_cu", 100))
    write_cu = int(request.args.get("write_cu", 50))
    period = int(request.args.get("period", 1))
    result = query_tablestore_price(region_id, storage_gb, read_cu, write_cu, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/hbr", methods=["GET"])
def api_hbr_price():
    region_id = request.args.get("region_id", "cn-beijing")
    storage_gb = int(request.args.get("storage_gb", 500))
    period = int(request.args.get("period", 1))
    result = query_hbr_price(region_id, storage_gb, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/bastionhost", methods=["GET"])
def api_bastionhost_price():
    region_id = request.args.get("region_id", "cn-beijing")
    edition = request.args.get("edition", "basic")
    period = int(request.args.get("period", 1))
    result = query_bastionhost_price(region_id, edition, period)
    return jsonify({"success": result.get("success", False), "data": result})


@app.route("/api/pricing/batch", methods=["POST"])
def api_batch_price():
    body = request.get_json(force=True)
    region_id = body.get("region_id", "cn-beijing")
    period = body.get("period", 1)
    items = body.get("items", [])

    if not items:
        return jsonify({"success": False, "message": "items cannot be empty"})

    prices = batch_query(items, region_id, period)

    # Summary
    total_original = sum(p.get("total_price", 0) for p in prices if p.get("success"))
    total_trade = sum(p.get("total_trade_price", 0) for p in prices if p.get("success"))
    success_count = sum(1 for p in prices if p.get("success"))
    fail_count = sum(1 for p in prices if not p.get("success"))

    return jsonify({
        "success": True,
        "data": {
            "prices": prices,
            "summary": {
                "total_original_price": total_original,
                "total_trade_price": total_trade,
                "total_discount": total_original - total_trade,
                "currency": "CNY",
                "success_count": success_count,
                "fail_count": fail_count,
                "region_id": region_id,
                "period": period,
                "period_unit": "Year" if period >= 12 else "Month",
            },
        },
    })


@app.route("/api/pricing/products", methods=["GET"])
def api_products():
    """Get supported products and specs list"""
    return jsonify({
        "success": True,
        "data": {
            "products": [
                {
                    "code": "ecs", "name": "Cloud Server ECS",
                    "common_specs": [
                        "ecs.g7.large", "ecs.g7.xlarge", "ecs.g7.2xlarge", "ecs.g7.4xlarge",
                        "ecs.c7.large", "ecs.c7.xlarge", "ecs.c7.2xlarge", "ecs.c7.4xlarge",
                        "ecs.r7.large", "ecs.r7.xlarge", "ecs.r7.2xlarge", "ecs.r7.4xlarge",
                        "ecs.g8i.large", "ecs.g8i.xlarge", "ecs.g8i.2xlarge",
                    ],
                },
                {
                    "code": "rds", "name": "ApsaraDB RDS",
                    "common_specs": [
                        "rds.mysql.s2.large", "rds.mysql.s3.large", "rds.mysql.m1.medium",
                        "rds.mysql.c1.large", "rds.mysql.c1.xlarge",
                        "pg.n2.small.2c", "pg.n2.medium.2c",
                    ],
                },
                {
                    "code": "redis", "name": "ApsaraDB Redis",
                    "common_specs": [
                        "redis.master.small.default", "redis.master.mid.default",
                        "redis.master.stand.default", "redis.master.large.default",
                        "redis.master.2xlarge.default",
                    ],
                },
                {
                    "code": "slb", "name": "Load Balancer SLB",
                    "common_specs": [
                        "slb.s1.small", "slb.s2.small", "slb.s2.medium",
                        "slb.s3.small", "slb.s3.medium", "slb.s3.large",
                    ],
                },
                {
                    "code": "polardb", "name": "PolarDB Database",
                    "common_specs": [
                        "polar.mysql.g2.medium", "polar.mysql.g2.large", "polar.mysql.g2.xlarge",
                        "polar.mysql.g4.xlarge", "polar.mysql.g8.xlarge", "polar.mysql.g8.2xlarge",
                        "polar.pg.g2.medium", "polar.pg.g2.large", "polar.pg.g4.xlarge",
                    ],
                },
                {
                    "code": "mongodb", "name": "ApsaraDB MongoDB",
                    "common_specs": [
                        "mdb.shard.2x.large.d", "mdb.shard.2x.xlarge.d",
                        "mdb.shard.2x.2xlarge.d", "mdb.shard.2x.4xlarge.d",
                    ],
                },
                {
                    "code": "elasticsearch", "name": "Elasticsearch",
                    "common_specs": [
                        "elasticsearch.sn2ne.large", "elasticsearch.sn2ne.xlarge",
                        "elasticsearch.sn2ne.2xlarge", "elasticsearch.sn1ne.large",
                    ],
                },
                {
                    "code": "gpdb", "name": "AnalyticDB PostgreSQL",
                    "common_specs": [
                        "gpdb.group.segsdx1", "gpdb.group.segsdx2",
                    ],
                },
                {
                    "code": "oss", "name": "Object Storage OSS",
                    "storage_classes": [
                        {"code": "Standard", "name": "Standard Storage", "ref_price": "0.12CNY/GB/Month"},
                        {"code": "IA", "name": "Infrequent Access", "ref_price": "0.08CNY/GB/Month"},
                        {"code": "Archive", "name": "Archive Storage", "ref_price": "0.033CNY/GB/Month"},
                        {"code": "ColdArchive", "name": "Cold Archive", "ref_price": "0.015CNY/GB/Month"},
                        {"code": "DeepColdArchive", "name": "Deep Cold Archive", "ref_price": "0.0045CNY/GB/Month"},
                    ],
                    "usage": "Pass in storage_class and capacity_gb parameters for pricing",
                },
                {
                    "code": "disk", "name": "Block Storage Cloud Disk",
                    "disk_categories": [
                        {"code": "cloud_essd", "name": "ESSD Cloud Disk", "performance_levels": ["PL0", "PL1", "PL2", "PL3"]},
                        {"code": "cloud_essd_entry", "name": "ESSD Entry"},
                        {"code": "cloud_ssd", "name": "SSD Cloud Disk"},
                        {"code": "cloud_efficiency", "name": "Ultra Cloud Disk"},
                        {"code": "cloud_auto", "name": "ESSD AutoPL"},
                    ],
                    "usage": "Pass in disk_category, disk_size, performance_level parameter",
                },
                {
                    "code": "nas", "name": "File Storage NAS",
                    "storage_types": [
                        {"code": "Capacity", "name": "Capacity", "price": "0.35CNY/GB/Month"},
                        {"code": "Performance", "name": "Performance", "price": "1.85CNY/GB/Month"},
                        {"code": "Extreme", "name": "Ultra", "price": "1.80CNY/GB/Month"},
                        {"code": "ExtremeAdvance", "name": "Ultra Advanced", "price": "0.92CNY/GB/Month"},
                        {"code": "General", "name": "General Purpose", "price": "0.15CNY/GB/Month"},
                    ],
                    "usage": "Pass in storage_type and capacity_gb parameters for pricing",
                },
                {
                    "code": "kafka", "name": "Message Queue Kafka",
                    "pricing": "BSSReal-time pricing",
                    "common_specs": ["professional-20MB", "professional-60MB", "professional-120MB"],
                },
                {
                    "code": "rocketmq", "name": "Message Queue RocketMQ",
                    "pricing": "Official reference price",
                    "common_specs": ["2000tps", "5000tps", "10000tps", "20000tps"],
                },
                {
                    "code": "rabbitmq", "name": "Message Queue RabbitMQ",
                    "pricing": "Official reference price",
                    "common_specs": ["professional-1000", "professional-5000", "enterprise-10000"],
                },
                {
                    "code": "waf", "name": "WebApplication Firewall WAF",
                    "pricing": "BSSReal-time pricing",
                    "common_specs": ["pro_asia", "business_asia", "ultimate_asia"],
                },
                {
                    "code": "ddos", "name": "DDoSProtection",
                    "pricing": "BSSReal-time pricing",
                    "common_specs": ["bgp-20G-100IP", "coo-30G"],
                },
                {
                    "code": "bastionhost", "name": "Bastion Host",
                    "pricing": "Official reference price",
                    "common_specs": ["basic", "standard", "advanced"],
                },
                {
                    "code": "vpn", "name": "VPNGateway",
                    "pricing": "Official reference price",
                    "common_specs": ["5M", "10M", "20M", "50M", "100M"],
                },
                {
                    "code": "cdn", "name": "CDNCDN",
                    "pricing": "Official reference price(Tiered billing)",
                    "usage": "Pass in bandwidth_mbps parameter",
                },
                {
                    "code": "emr", "name": "E-MapReduce",
                    "pricing": "Official reference price(Management fee)",
                    "common_specs": ["emr.c6.xlarge", "emr.c6.2xlarge", "emr.c6.4xlarge"],
                },
                {
                    "code": "flink", "name": "Realtime ComputeFlink",
                    "pricing": "Official reference price(byCU)",
                    "usage": "Pass in cu_count parameter",
                },
                {
                    "code": "sls", "name": "Log Service SLS",
                    "pricing": "Official reference price",
                    "usage": "Pass in ingest_gb_day, retention_days parameter",
                },
                {
                    "code": "maxcompute", "name": "MaxCompute Big Data Compute",
                    "pricing": "Official reference price",
                    "usage": "Pass in cu_count, storage_tb parameter",
                },
                {
                    "code": "ack", "name": "Container Service ACK",
                    "pricing": "Official reference price(Management fee)",
                    "common_specs": ["standard", "pro", "serverless"],
                },
                {
                    "code": "eci", "name": "Elastic Container Instance ECI",
                    "pricing": "Pay-as-you-go reference price",
                    "usage": "Pass in cpu, memory_gb, hours_per_month parameter",
                },
                {
                    "code": "fc", "name": "Function Compute FC",
                    "pricing": "Pay-as-you-go reference price",
                    "usage": "Pass in memory_mb, invocations_million, duration_seconds parameter",
                },
                {
                    "code": "sae", "name": "ServerlessApplication Engine SAE",
                    "pricing": "Pay-as-you-go reference price",
                    "usage": "Pass in cpu, memory_gb, instances parameter",
                },
                {
                    "code": "lindorm", "name": "Lindorm Multi-model Database",
                    "pricing": "Official reference price",
                    "common_specs": ["lindorm.c.xlarge", "lindorm.c.2xlarge", "lindorm.c.4xlarge"],
                },
                {
                    "code": "gdb", "name": "Graph Database GDB",
                    "pricing": "Official reference price",
                    "common_specs": ["gdb.r.xlarge", "gdb.r.2xlarge", "gdb.r.4xlarge"],
                },
                {
                    "code": "tablestore", "name": "Tablestore Tablestore",
                    "pricing": "Pay-as-you-go reference price",
                    "usage": "Pass in storage_gb, read_cu, write_cu parameter",
                },
                {
                    "code": "hbr", "name": "Cloud Backup HBR",
                    "pricing": "Official reference price",
                    "usage": "Pass in storage_gb parameter，0.1CNY/GB/Month",
                },
            ],
            "regions": [
                {"id": "cn-beijing", "name": "North China2（Beijing）"},
                {"id": "cn-hangzhou", "name": "East China1（Hangzhou）"},
                {"id": "cn-shanghai", "name": "East China2（Shanghai）"},
                {"id": "cn-shenzhen", "name": "South China1（Shenzhen）"},
                {"id": "cn-guangzhou", "name": "South China3（Guangzhou）"},
                {"id": "cn-chengdu", "name": "Southwest China1（Chengdu）"},
                {"id": "cn-hongkong", "name": "Hong Kong"},
                {"id": "ap-southeast-1", "name": "Singapore"},
                {"id": "us-east-1", "name": "US（Virginia）"},
                {"id": "eu-central-1", "name": "Germany（Frankfurt）"},
            ],
        },
    })


@app.route("/health", methods=["GET"])
def health():
    ak, sk = get_credentials()
    return jsonify({
        "status": "ok",
        "credentials_configured": bool(ak and sk),
        "service": "pricing-service",
        "version": "1.0.0",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PRICING_PORT", 5000))
    print(f"🚀 Alibaba Cloud Pricing Service started: http://0.0.0.0:{port}")
    print(f"   Health check: http://localhost:{port}/health")
    print(f"   Batch Pricing: POST http://localhost:{port}/api/pricing/batch")
    app.run(host="0.0.0.0", port=port, debug=False)
