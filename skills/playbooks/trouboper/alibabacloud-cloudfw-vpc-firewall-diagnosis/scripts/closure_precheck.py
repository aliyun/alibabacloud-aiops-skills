#!/usr/bin/env python3
"""VPC firewall closure pre-check diagnostic script.

The script compares the CFW policy route table with the system route table and identifies route entries that may be lost after closure.
All Alibaba Cloud CLI calls are read-only and use lowercase-hyphenated plugin actions.
"""

import json
import subprocess
import sys

USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis"


def run_cli(argv):
    """Run a CLI command with shell=False and return the JSON response."""
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        print(f"Error: run_cli only accepts a list[str], got {type(argv).__name__}")
        sys.exit(1)
    try:
        result = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Error: command failed: {result.stderr}")
            sys.exit(1)

        output = result.stdout
        json_start = output.find("{")
        if json_start == -1:
            print("Error: JSON output was not found")
            sys.exit(1)
        return json.loads(output[json_start:])
    except Exception as exc:
        print(f"Error: execution exception: {exc}")
        sys.exit(1)


def with_user_agent(args):
    return args + ["--user-agent", USER_AGENT]


def get_vpc_firewall_info(profile, region):
    """Step 1: get VPC firewall information."""
    print("=" * 80)
    print("Step 1: Get VPC firewall information")
    print("=" * 80)

    cmd = with_user_agent([
        "aliyun", "--profile", profile, "cloudfw",
        "describe-tr-firewalls-v2-list", "--RegionId", region,
    ])
    data = run_cli(cmd)

    if data.get("TotalCount", 0) == 0:
        print("Error: no VPC firewall was found")
        sys.exit(1)

    firewall = data["VpcTrFirewalls"][0]
    print(f"Firewall ID: {firewall['FirewallId']}")
    print(f"Transit router ID: {firewall['TransitRouterId']}")
    print(f"CEN ID: {firewall['CenId']}")
    print(f"Protected VPC count: {firewall['ProtectedResource']['Count']}")
    print(f"Unprotected VPC count: {firewall['UnprotectedResource']['Count']}")
    print()
    return firewall


def get_route_tables(profile, region, transit_router_id):
    """Step 2: get transit router route tables."""
    print("=" * 80)
    print("Step 2: Get route table list")
    print("=" * 80)

    cmd = with_user_agent([
        "aliyun", "--profile", profile, "cbn",
        "list-transit-router-route-tables",
        "--RegionId", region,
        "--TransitRouterId", transit_router_id,
    ])
    data = run_cli(cmd)

    system_table = None
    cfw_policy_table = None
    for table in data.get("TransitRouterRouteTables", []):
        table_type = table.get("TransitRouterRouteTableType")
        description = table.get("TransitRouterRouteTableDescription", "")
        if table_type == "System":
            system_table = table
            print(f"System route table: {table['TransitRouterRouteTableId']}")
        elif "firewall_id" in description and "policy_id" in description:
            cfw_policy_table = table
            print(f"CFW policy route table: {table['TransitRouterRouteTableId']}")
            print(f"Description: {description}")

    if not system_table or not cfw_policy_table:
        print("Error: required route tables were not found")
        sys.exit(1)

    print()
    return system_table, cfw_policy_table


def get_route_entries(profile, route_table_id, table_name):
    """Step 3: get route entries with data completeness validation."""
    print("=" * 80)
    print(f"Step 3: Get {table_name} route entries")
    print("=" * 80)

    cmd = with_user_agent([
        "aliyun", "--profile", profile, "cbn",
        "list-transit-router-route-entries",
        "--TransitRouterRouteTableId", route_table_id,
        "--MaxResults", "100",
    ])
    data = run_cli(cmd)

    total_count = data.get("TotalCount", 0)
    entries = data.get("TransitRouterRouteEntries", [])
    actual_count = len(entries)
    print(f"TotalCount: {total_count}")
    print(f"Returned entries: {actual_count}")
    if total_count != actual_count:
        print(f"Warning: returned data may be incomplete. TotalCount={total_count}, returned={actual_count}.")
        print("Warning: pagination may be required; only returned route entries are analyzed.")
    else:
        print("Data completeness validation passed")

    print()
    return entries


def filter_cfw_auto_routes(routes):
    """Filter CFW auto-generated routes using both OperationalMode and description conditions."""
    auto_routes = []
    business_routes = []
    for route in routes:
        operational_mode = route.get("OperationalMode", False)
        description = route.get("TransitRouterRouteEntryDescription", "").lower()
        if operational_mode is True and "cloud_firewall" in description:
            auto_routes.append(route)
        else:
            business_routes.append(route)
    return auto_routes, business_routes


def compare_routes(cfw_business_routes, system_routes):
    """Step 4: compare route tables and identify missing routes."""
    print("=" * 80)
    print("Step 4: Route comparison")
    print("=" * 80)

    system_set = set()
    for route in system_routes:
        cidr = route["TransitRouterRouteEntryDestinationCidrBlock"]
        next_hop = route.get("TransitRouterRouteEntryNextHopResourceId", "")
        system_set.add((cidr, next_hop))

    print(f"System route count: {len(system_set)}")
    print(f"CFW business route count: {len(cfw_business_routes)}")
    print()

    missing_routes = []
    for route in cfw_business_routes:
        cidr = route["TransitRouterRouteEntryDestinationCidrBlock"]
        next_hop = route.get("TransitRouterRouteEntryNextHopResourceId", "")
        if (cidr, next_hop) not in system_set:
            missing_routes.append({
                "cidr": cidr,
                "next_hop": next_hop,
                "type": route.get("TransitRouterRouteEntryType", ""),
                "name": route.get("TransitRouterRouteEntryName", ""),
                "description": route.get("TransitRouterRouteEntryDescription", ""),
            })
    return missing_routes


def check_acl_policies(profile, firewall_id):
    """Step 5: check ACL policies."""
    print("=" * 80)
    print("Step 5: Check ACL policies")
    print("=" * 80)

    cmd = with_user_agent([
        "aliyun", "--profile", profile, "cloudfw",
        "describe-vpc-firewall-control-policy",
        "--VpcFirewallId", firewall_id,
        "--PageSize", "50",
        "--CurrentPage", "1",
    ])
    data = run_cli(cmd)

    total_count = data.get("TotalCount", 0)
    print(f"ACL policy count: {total_count}")
    if total_count == 0:
        print("Warning: no ACL policy is configured.")
        print("Risk: traffic may be denied by default when the firewall is enabled again without ACL policies.")
    else:
        print(f"{total_count} ACL policies are configured")
    print()
    return total_count


def generate_report(missing_routes, acl_count):
    """Generate the pre-check report."""
    print("=" * 80)
    print("VPC firewall closure pre-check report")
    print("=" * 80)
    print()

    risk_level = "HIGH" if missing_routes else "LOW"
    print(f"Risk level: {risk_level}")
    print(f"Business routes that may be lost after closure: {len(missing_routes)}")
    print()

    if missing_routes:
        print("Routes that may be lost after closure:")
        print("| Destination CIDR | Next-hop VPC | Route type | Route name | Impact |")
        print("|---|---|---|---|---|")
        for route in missing_routes:
            print(f"| {route['cidr']} | {route['next_hop']} | {route['type']} | {route['name'] or '-'} | High |")
        print()
        print("Impact analysis:")
        for index, route in enumerate(missing_routes, 1):
            print(f"{index}. {route['cidr']} -> {route['next_hop']}")
            print(f"   Route type: {route['type']}")
            if route["name"]:
                print(f"   Route name: {route['name']}")
            if route["description"]:
                print(f"   Description: {route['description']}")
            print(f"   Impact: traffic to {route['cidr']} may become unroutable after closure.")
    else:
        print("No business route is expected to be lost after closure.")

    print()
    print("ACL policy status:")
    if acl_count == 0:
        print("  Warning: no ACL policy is configured. Prepare temporary allow rules before re-enabling the firewall if needed.")
    else:
        print(f"  {acl_count} ACL policies are configured.")

    print()
    print("=" * 80)
    print("Recommended manual actions")
    print("=" * 80)
    if missing_routes:
        print("1. Before closure, prepare temporary ACL allow policies in the console.")
        print("2. Before closure, address the route loss risk manually:")
        for route in missing_routes:
            print(f"   - {route['cidr']} -> {route['next_hop']}")
            print("     Option A: manually add the static route to the system route table after review.")
            print("     Option B: add the next-hop VPC into the CFW protected scope after review.")
        print("3. Confirm whether business traffic to the affected CIDRs can tolerate interruption.")
    else:
        print("1. Closure appears safe from a route rollback perspective.")
        print("2. Still review ACL policies before closure and before any later re-enable operation.")
    print("3. After closure, verify route restoration and key business connectivity.")
    print("4. Monitor for 1 to 2 hours to confirm that no business impact appears.")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 closure_precheck.py <profile> <region>")
        print("Example: python3 closure_precheck.py default cn-hangzhou")
        sys.exit(1)

    profile = sys.argv[1]
    region = sys.argv[2]
    firewall = get_vpc_firewall_info(profile, region)
    system_table, cfw_policy_table = get_route_tables(profile, region, firewall["TransitRouterId"])
    cfw_routes = get_route_entries(profile, cfw_policy_table["TransitRouterRouteTableId"], "CFW policy")
    system_routes = get_route_entries(profile, system_table["TransitRouterRouteTableId"], "system")
    cfw_auto, cfw_business = filter_cfw_auto_routes(cfw_routes)
    print(f"CFW auto routes filtered: {len(cfw_auto)}")
    print(f"CFW business routes: {len(cfw_business)}")
    print()
    missing_routes = compare_routes(cfw_business, system_routes)
    acl_count = check_acl_policies(profile, firewall["FirewallId"])
    generate_report(missing_routes, acl_count)


if __name__ == "__main__":
    main()
