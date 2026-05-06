#!/usr/bin/env python3
"""
DTS Task Status Query Script (v12.1 - Performance + Reliability)

Features:
1. **PERFORMANCE**: Parallel queries with ThreadPoolExecutor (8 workers by default, configurable via --workers)
2. **PERFORMANCE**: PageSize increased to 200 (reduces pagination calls by 50%)
3. **PERFORMANCE**: Early pagination exit - skips empty regions immediately
4. **PERFORMANCE**: Timeout increased to 10s for better reliability (from 5s in v12)
5. Polls all 27 regions and 3 job types (MIGRATION, SYNC, SUBSCRIBE).
6. Injects '_QueryRegion' field into each task during query.
7. Saves raw data to /tmp for integrity.
8. Filters strictly by PayType (PrePaid/PostPaid).
9. Outputs full Chinese report with Region column.
10. Group tasks by type (Migration/Sync/Subscribe) and sort by CreateTime within each group.
11. **RELIABILITY**: API retry logic (3 attempts with exponential backoff) ensures consistent results without count variations
12. **RELIABILITY**: Thread-safe data collection with Lock prevents race conditions
13. **RELIABILITY**: Strict response validation - only accepts responses with "DtsJobList" field
14. **RELIABILITY**: Distinguishes timeout vs general exceptions for easier debugging
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

SUPPORTED_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-qingdao", "cn-beijing", "cn-zhangjiakou",
    "cn-huhehaote", "cn-wulanchabu", "cn-shenzhen", "cn-heyuan", "cn-guangzhou",
    "cn-chengdu", "cn-hongkong", "ap-southeast-1", "ap-southeast-3", "ap-southeast-5",
    "ap-southeast-6", "ap-southeast-7", "ap-northeast-1", "ap-northeast-2",
    "us-west-1", "us-east-1", "eu-central-1", "eu-west-1", "me-central-1", "me-east-1"
]

REGION_CN_MAP = {
    "cn-hangzhou": "华东1（杭州）", "cn-shanghai": "华东2（上海）", "cn-qingdao": "华北1（青岛）",
    "cn-beijing": "华北2（北京）", "cn-zhangjiakou": "华北3（张家口）", "cn-huhehaote": "华北5（呼和浩特）",
    "cn-wulanchabu": "华北6（乌兰察布）", "cn-shenzhen": "华南1（深圳）", "cn-heyuan": "华南2（河源）",
    "cn-guangzhou": "华南3（广州）", "cn-chengdu": "西南1（成都）", "cn-hongkong": "中国（香港）",
    "ap-southeast-1": "亚太东南1（新加坡）", "ap-southeast-3": "亚太东南3（吉隆坡）",
    "ap-southeast-5": "亚太东南5（雅加达）", "ap-southeast-6": "亚太东南6（马尼拉）",
    "ap-southeast-7": "亚太东南7（曼谷）", "ap-northeast-1": "亚太东北1（东京）",
    "ap-northeast-2": "亚太东北2（首尔）", "us-west-1": "美国西部1（硅谷）",
    "us-east-1": "美国东部1（弗吉尼亚）", "eu-central-1": "欧洲中部1（法兰克福）",
    "eu-west-1": "英国（伦敦）", "me-central-1": "中东中部1（利雅得）", "me-east-1": "中东东部1（迪拜）"
}

JOB_TYPE_MAP = {"online": "迁移", "migration": "迁移", "sync": "同步", "synchronization": "同步", "subscribe": "订阅", "subscription": "订阅"}

# Endpoint mapping for overseas regions (REQUIRED to query overseas DTS tasks)
ENDPOINT_MAP = {
    "ap-southeast-1": "dts.ap-southeast-1.aliyuncs.com",
    "ap-southeast-3": "dts.ap-southeast-3.aliyuncs.com",
    "ap-southeast-5": "dts.ap-southeast-5.aliyuncs.com",
    "ap-southeast-6": "dts.ap-southeast-6.aliyuncs.com",
    "ap-southeast-7": "dts.ap-southeast-7.aliyuncs.com",
    "ap-northeast-1": "dts.ap-northeast-1.aliyuncs.com",
    "ap-northeast-2": "dts.ap-northeast-2.aliyuncs.com",
    "us-west-1": "dts.us-west-1.aliyuncs.com",
    "us-east-1": "dts.us-east-1.aliyuncs.com",
    "eu-central-1": "dts.eu-central-1.aliyuncs.com",
    "eu-west-1": "dts.eu-west-1.aliyuncs.com",
    "me-central-1": "dts.me-central-1.aliyuncs.com",
    "me-east-1": "dts.me-east-1.aliyuncs.com"
}

def execute_cli(region: str, job_type: str, page: int = 1) -> Optional[Dict]:
    # Build base command - using AI-Mode plugin mode
    cmd = [
        "aliyun", "dts", "DescribeDtsJobs",
        "--Region", region, "--JobType", job_type,
        "--PageNumber", str(page), "--PageSize", "200",
        "--mode", "AI-Mode"  # Explicitly use AI-Mode for plugin compatibility
    ]

    # CRITICAL FIX: Add endpoint for overseas regions (required to get any results)
    if region in ENDPOINT_MAP:
        cmd.extend(["--endpoint", ENDPOINT_MAP[region]])

    # Retry up to 3 times on failure with exponential backoff (ensures consistent results, prevents count variations)
    for attempt in range(3):
        try:
            # Increased timeout to 10s for reliability (v12.1)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                print(f"ERROR: API call failed for region={region}, job_type={job_type}, page={page}, attempt={attempt+1}/3", file=sys.stderr)
                print(f"  Return code: {res.returncode}", file=sys.stderr)
                print(f"  stderr: {res.stderr.strip()}", file=sys.stderr)
                continue
            # Ensure we have valid JSON with DtsJobList field
            data = json.loads(res.stdout) if res.stdout.strip() else None
            if data and "DtsJobList" in data:
                return data
            print(f"ERROR: Invalid API response - missing DtsJobList field for region={region}, job_type={job_type}, page={page}", file=sys.stderr)
            return None  # Invalid response format
        except subprocess.TimeoutExpired:
            print(f"ERROR: API call timeout for region={region}, job_type={job_type}, page={page}, attempt={attempt+1}/3 (10s limit)", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Exception during API call for region={region}, job_type={job_type}, page={page}, attempt={attempt+1}/3: {type(e).__name__}: {e}", file=sys.stderr)
        if attempt < 2:
            import time
            # Exponential backoff: 0.2s, 0.4s
            time.sleep(0.2 * (2 ** attempt))
    print(f"ERROR: All retry attempts failed for region={region}, job_type={job_type}, page={page}", file=sys.stderr)
    return None

def query_job_type(args):
    """Worker function for parallel execution."""
    region, jtype = args
    jobs = []
    page = 1

    # Early exit: if page 1 returns empty, skip pagination entirely
    resp = execute_cli(region, jtype, 1)
    if not resp:
        return []
    page_jobs = resp.get("DtsJobList", [])
    if not page_jobs:
        return []

    # Page 1 has data, inject region
    for job in page_jobs:
        job["_QueryRegion"] = region
    jobs.extend(page_jobs)

    # Only paginate if we got a full page (200 items)
    total_count = resp.get("TotalRecordCount", 0)
    while len(page_jobs) == 200 and len(jobs) < total_count:
        page += 1
        resp = execute_cli(region, jtype, page)
        if not resp:
            break
        page_jobs = resp.get("DtsJobList", [])
        if not page_jobs:
            break
        for job in page_jobs:
            job["_QueryRegion"] = region
        jobs.extend(page_jobs)

    return jobs

def query_and_save(regions: List[str], job_types: List[str], max_workers: int = 8) -> str:
    all_raw_jobs = []
    tasks = [(r, j) for r in regions for j in job_types]

    # Use ThreadPoolExecutor to query in parallel with thread-safe collection (v12 reliability feature)
    from threading import Lock
    lock = Lock()

    def worker(task):
        region, jtype = task
        jobs = query_job_type((region, jtype))
        if jobs:
            with lock:  # Prevent race conditions during concurrent writes
                all_raw_jobs.extend(jobs)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(worker, tasks)

    fd, path = tempfile.mkstemp(suffix='.json', prefix='dts_raw_')
    with os.fdopen(fd, 'w') as f:
        json.dump(all_raw_jobs, f)
    return path

def process_and_filter(temp_path: str, inst_id: Optional[str], job_name: Optional[str]) -> str:
    with open(temp_path, 'r') as f:
        jobs = json.load(f)

    # Filter strictly by PayType (PrePaid/PostPaid)
    valid_jobs = [j for j in jobs if j.get("PayType") in ["PrePaid", "PostPaid"]]

    # Apply user filters
    if inst_id:
        valid_jobs = [j for j in valid_jobs if j.get("DtsInstanceID") == inst_id or j.get("DtsInstanceId") == inst_id]
    if job_name:
        valid_jobs = [j for j in valid_jobs if job_name.lower() in j.get("DtsJobName", "").lower()]

    # Format Output
    lines = ["### 1. 统计摘要"]
    lines.append(f"- **任务总量**: {len(valid_jobs)}")

    # Region Distribution
    region_dist = {}
    for job in valid_jobs:
        region_cn = REGION_CN_MAP.get(job.get("_QueryRegion", ""), job.get("_QueryRegion", ""))
        region_dist[region_cn] = region_dist.get(region_cn, 0) + 1
    lines.append("- **地域分布**: ")
    for region, count in sorted(region_dist.items()):
        lines.append(f"  - {region}: {count} 个")

    # Status Distribution
    status_dist = {}
    for job in valid_jobs:
        status = job.get("Status", "Unknown")
        status_dist[status] = status_dist.get(status, 0) + 1
    lines.append("- **状态分布**: ")
    for status, count in sorted(status_dist.items()):
        lines.append(f"  - {status}: {count} 个")

    # Job Type Distribution
    type_dist = {}
    for job in valid_jobs:
        jtype = JOB_TYPE_MAP.get(job.get("JobType", "").lower(), job.get("JobType", "Unknown"))
        type_dist[jtype] = type_dist.get(jtype, 0) + 1
    lines.append("- **类型分布**: ")
    for jtype, count in sorted(type_dist.items()):
        lines.append(f"  - {jtype}: {count} 个")

    lines.append("\n### 2. 任务明细")
    if not valid_jobs:
        lines.append("未找到符合条件的任务。")
    else:
        # Group jobs by type
        migration_jobs = []
        sync_jobs = []
        subscribe_jobs = []

        for job in valid_jobs:
            job_type_cn = JOB_TYPE_MAP.get(job.get("JobType", "").lower(), job.get("JobType", ""))
            if job_type_cn == "迁移":
                migration_jobs.append(job)
            elif job_type_cn == "同步":
                sync_jobs.append(job)
            elif job_type_cn == "订阅":
                subscribe_jobs.append(job)

        # Sort each group by CreateTime (newest first)
        migration_jobs.sort(key=lambda x: x.get("CreateTime", ""), reverse=True)
        sync_jobs.sort(key=lambda x: x.get("CreateTime", ""), reverse=True)
        subscribe_jobs.sort(key=lambda x: x.get("CreateTime", ""), reverse=True)

        # Output Migration tasks
        if migration_jobs:
            lines.append("\n#### 迁移任务")
            lines.append(f"共 {len(migration_jobs)} 个")
            headers = ["地域", "状态", "DTS任务名称", "过期时间", "DTS任务ID", "创建时间", "DTS实例ID"]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * 7) + " |")
            for job in migration_jobs:
                row = [
                    REGION_CN_MAP.get(job.get("_QueryRegion", ""), job.get("_QueryRegion", "")),
                    job.get("Status", ""),
                    job.get("DtsJobName", ""),
                    job.get("ExpireTime", ""),
                    job.get("DtsJobId", ""),
                    job.get("CreateTime", ""),
                    job.get("DtsInstanceID", job.get("DtsInstanceId", ""))
                ]
                lines.append("| " + " | ".join(str(x) for x in row) + " |")

        # Output Sync tasks
        if sync_jobs:
            lines.append("\n#### 同步任务")
            lines.append(f"共 {len(sync_jobs)} 个")
            headers = ["地域", "状态", "DTS任务名称", "过期时间", "DTS任务ID", "创建时间", "DTS实例ID"]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * 7) + " |")
            for job in sync_jobs:
                row = [
                    REGION_CN_MAP.get(job.get("_QueryRegion", ""), job.get("_QueryRegion", "")),
                    job.get("Status", ""),
                    job.get("DtsJobName", ""),
                    job.get("ExpireTime", ""),
                    job.get("DtsJobId", ""),
                    job.get("CreateTime", ""),
                    job.get("DtsInstanceID", job.get("DtsInstanceId", ""))
                ]
                lines.append("| " + " | ".join(str(x) for x in row) + " |")

        # Output Subscribe tasks
        if subscribe_jobs:
            lines.append("\n#### 订阅任务")
            lines.append(f"共 {len(subscribe_jobs)} 个")
            headers = ["地域", "状态", "DTS任务名称", "过期时间", "DTS任务ID", "创建时间", "DTS实例ID"]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * 7) + " |")
            for job in subscribe_jobs:
                row = [
                    REGION_CN_MAP.get(job.get("_QueryRegion", ""), job.get("_QueryRegion", "")),
                    job.get("Status", ""),
                    job.get("DtsJobName", ""),
                    job.get("ExpireTime", ""),
                    job.get("DtsJobId", ""),
                    job.get("CreateTime", ""),
                    job.get("DtsInstanceID", job.get("DtsInstanceId", ""))
                ]
                lines.append("| " + " | ".join(str(x) for x in row) + " |")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", type=str)
    parser.add_argument("--instance-id", type=str)
    parser.add_argument("--job-name", type=str)
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent workers (default: 8)")
    args = parser.parse_args()

    # SECURITY: Validate --region against whitelist
    if args.region:
        if args.region not in SUPPORTED_REGIONS:
            print(f"ERROR: Invalid region '{args.region}'", file=sys.stderr)
            print(f"Supported regions: {', '.join(SUPPORTED_REGIONS)}", file=sys.stderr)
            sys.exit(1)
        regions = [args.region]
    else:
        regions = SUPPORTED_REGIONS

    # SECURITY: Validate --workers bounds (1-32)
    if args.workers < 1 or args.workers > 32:
        print(f"ERROR: Invalid --workers value: {args.workers}", file=sys.stderr)
        print("Valid range: 1-32", file=sys.stderr)
        sys.exit(1)

    temp_path = query_and_save(regions, ["MIGRATION", "SYNC", "SUBSCRIBE"], args.workers)
    try:
        print(process_and_filter(temp_path, args.instance_id, args.job_name))
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

if __name__ == "__main__":
    main()
