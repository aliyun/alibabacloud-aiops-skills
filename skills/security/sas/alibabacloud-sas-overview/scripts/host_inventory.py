#!/usr/bin/env python3
"""Read all host pages through aliyun CLI; never label partial data complete."""
import argparse
import json
import subprocess
import sys

try:
    from .cli_query import run_query
except ImportError:
    from cli_query import run_query


def fetch_page(region, page, page_size, user_agent):
    command = ["aliyun", "sas", "describe-cloud-center-instances", "--region", region,
               "--machine-types", "ecs", "--current-page", str(page),
               "--page-size", str(page_size), "--user-agent", user_agent]
    return run_query(command, progress=lambda message: print(message, file=sys.stderr, flush=True))


def nonnegative_int(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"Invalid {field}")
    if isinstance(value, str) and not value.isdecimal():
        raise ValueError(f"Invalid {field}")
    value = int(value)
    if value < 0:
        raise ValueError(f"Invalid {field}")
    return value


def collect_region(region, user_agent, fetch=fetch_page, page_size=20, progress=None):
    count, cores, expected = 0, 0, None
    seen = set()
    request_id = None
    try:
        for page in range(1, 10001):
            if progress:
                progress(f"{region}: page {page}; collected {count}/{expected if expected is not None else '?'}")
            data = fetch(region, page, page_size, user_agent)
            if not isinstance(data, dict):
                raise ValueError("Expected response object")
            request_id = data.get("RequestId")
            total = nonnegative_int(data["PageInfo"]["TotalCount"], "TotalCount")
            if expected is not None and expected != total:
                raise ValueError("TotalCount changed during pagination; restart the inventory")
            expected = total
            rows = data["Instances"]
            if not isinstance(rows, list) or len(rows) > page_size:
                raise ValueError("Invalid Instances page")
            page_ids, page_cores = set(), 0
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("Invalid instance object")
                uuid = row.get("Uuid")
                if not isinstance(uuid, str) or not uuid or uuid in seen or uuid in page_ids:
                    raise ValueError("Missing or repeated Uuid; inventory may have changed")
                page_ids.add(uuid)
                page_cores += nonnegative_int(row.get("Cores"), "Cores")
            if count + len(rows) > total:
                raise ValueError("Collected count exceeds TotalCount")
            seen.update(page_ids)
            count += len(rows)
            cores += page_cores
            if count == total:
                if progress:
                    progress(f"{region}: complete; collected {count}/{total}")
                return {"region": region, "complete": True, "total_count": total,
                        "collected_count": count, "cores": cores}
            if not rows:
                raise ValueError("Empty page before TotalCount reached")
        raise ValueError("Pagination limit reached")
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        if progress:
            progress(f"{region}: failed at page {page}; collected {count}/{expected}; partial")
        return {"region": region, "complete": False, "failed_page": page, "reported_total": expected,
                "collected_count": count, "partial_cores": cores,
                "request_id": request_id, "error": str(exc)}


def collect(regions, user_agent, fetch=fetch_page, progress=None):
    if not regions or len(regions) != len(set(regions)):
        raise ValueError("Specify distinct confirmed regions")
    results = [collect_region(region, user_agent, fetch, progress=progress) for region in regions]
    complete = all(row["complete"] for row in results)
    return {"complete": complete, "regions": results,
            "total_count": sum(row["total_count"] for row in results) if complete else None,
            "total_cores": sum(row["cores"] for row in results) if complete else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--user-agent", required=True)
    args = parser.parse_args()
    result = collect(args.regions, args.user_agent, progress=lambda message: print(message, file=sys.stderr, flush=True))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    sys.exit(main())
