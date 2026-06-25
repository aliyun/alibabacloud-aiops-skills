#!/usr/bin/env python3
"""VPC firewall closure pre-check analysis script.

Supported modes:
1. Auto-drainage with route rollback: filters Cloud Firewall auto-created split routes.
2. Manual-drainage with route rollback: compares all route entries.
3. Route revoke: identifies residual route tables that may require manual cleanup.
"""

import json
import sys


def load_routes(path):
    with open(path, "r", encoding="utf-8") as route_file:
        return json.load(route_file).get("TransitRouterRouteEntries", [])


def route_key(route):
    return (
        route.get("TransitRouterRouteEntryDestinationCidrBlock", ""),
        route.get("TransitRouterRouteEntryNextHopResourceId", ""),
    )


def print_validation(left_name, left_routes, right_name, right_routes):
    print("=" * 80)
    print("Data validation")
    print("=" * 80)
    print(f"{left_name} total route entries: {len(left_routes)}")
    print(f"{right_name} total route entries: {len(right_routes)}")


def print_route_risk(title, missing_routes, source_routes, extra_count, extra_label, target_label):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if missing_routes:
        print(f"\nHigh risk: {len(missing_routes)} route entries may be lost after closure.")
        print("\n{:<20} {:<40} {:<15} {:<10}".format("Destination", "Next hop", "Route type", "Risk"))
        print("-" * 85)
        details = []
        for destination, next_hop in sorted(missing_routes):
            route_info = next(
                (route for route in source_routes if route_key(route) == (destination, next_hop)),
                None,
            )
            if not route_info:
                continue
            route_type = route_info.get("TransitRouterRouteEntryType", "Unknown")
            next_hop_type = route_info.get("TransitRouterRouteEntryNextHopResourceType", "Unknown")
            risk = "HIGH" if next_hop_type in ["VPC", "VPN", "VBR"] else "MEDIUM"
            details.append((destination, next_hop, route_type, risk))
            print("{:<20} {:<40} {:<15} {:<10}".format(destination, next_hop, route_type, risk))

        high_risk = [item for item in details if item[3] == "HIGH"]
        medium_risk = [item for item in details if item[3] == "MEDIUM"]
        print("\n" + "=" * 80)
        print("Risk assessment")
        print("=" * 80)
        if high_risk:
            print(f"\nRisk level: HIGH")
            print(f"   - {len(high_risk)} high-risk route entries may be lost after closure.")
            print("   - The affected next hops include key network instances such as VPC, VPN, or VBR.")
            print(f"   - Add these route entries to the {target_label} before closure.")
        elif medium_risk:
            print(f"\nRisk level: MEDIUM")
            print(f"   - {len(medium_risk)} medium-risk route entries may be lost after closure.")
            print("   - Assess the business impact before closure.")
    else:
        print("\nRisk level: LOW")
        print("   - No business route difference was found.")
        print("   - No route entry is expected to be lost after closure.")

    if extra_count:
        print(f"\nInfo: {extra_count} route entries exist only in {extra_label}; this is expected and not directly affected.")

    print("\n" + "=" * 80)
    print("Recommended manual actions")
    print("=" * 80)
    if missing_routes:
        print(f"1. Before closure, manually add the missing route entries to the {target_label}.")
        print(f"2. Before closure, verify that the {target_label} has learned these routes.")
        print("3. Before closure, review ACL policies and define the post-closure access control plan.")
        print("4. After closure, monitor network traffic and verify business connectivity.")
        print("5. If any route is missing after closure, add the route manually after review.")
    else:
        print("1. Before closure, review ACL policies and the post-closure access control plan.")
        print("2. After closure, monitor network traffic and verify business connectivity.")


def analyze_routes_auto_rollback(cfw_routes_file, rollback_routes_file):
    cfw_all_routes = load_routes(cfw_routes_file)
    rollback_all_routes = load_routes(rollback_routes_file)
    print_validation("CFW policy route table", cfw_all_routes, "rollback target route table", rollback_all_routes)

    cfw_auto_routes = [
        route for route in cfw_all_routes
        if route.get("OperationalMode") and "cloud_firewall" in route.get("TransitRouterRouteEntryDescription", "").lower()
    ]
    cfw_business_routes = [route for route in cfw_all_routes if route not in cfw_auto_routes]
    print(f"\nCFW auto-created split routes: {len(cfw_auto_routes)} filtered")
    print(f"CFW business routes: {len(cfw_business_routes)}")
    print(f"Rollback target route table routes: {len(rollback_all_routes)}")

    cfw_business_set = {route_key(route) for route in cfw_business_routes}
    rollback_set = {route_key(route) for route in rollback_all_routes}
    missing_routes = cfw_business_set - rollback_set
    extra_in_rollback = rollback_set - cfw_business_set

    print_route_risk(
        "Closure pre-check result: auto-drainage with route rollback",
        missing_routes,
        cfw_business_routes,
        len(extra_in_rollback),
        "the rollback target route table",
        "rollback target route table",
    )


def analyze_routes_manual_rollback(current_routes_file, target_routes_file):
    current_all_routes = load_routes(current_routes_file)
    target_all_routes = load_routes(target_routes_file)
    print_validation("current route table", current_all_routes, "target route table", target_all_routes)
    print("\nManual-drainage mode: all route entries are compared without auto-route filtering.")

    current_set = {route_key(route) for route in current_all_routes}
    target_set = {route_key(route) for route in target_all_routes}
    missing_routes = current_set - target_set
    extra_in_target = target_set - current_set

    print_route_risk(
        "Closure pre-check result: manual-drainage with route rollback",
        missing_routes,
        current_all_routes,
        len(extra_in_target),
        "the target route table",
        "target route table",
    )


def analyze_route_revoke(route_tables_info_file):
    with open(route_tables_info_file, "r", encoding="utf-8") as route_file:
        route_tables_data = json.load(route_file)

    print("=" * 80)
    print("Closure pre-check result: route revoke mode")
    print("=" * 80)
    print("\nRisk level: LOW")
    print("   - Route revoke mode does not create route rollback loss risk.")
    print("   - Routes are removed from the transit router route table during closure.")
    print("\nAttention:")
    print("   - Empty route tables may remain in CEN after closure.")
    print("   - Review and clean residual route tables manually in the console if required.")

    print("\n" + "=" * 80)
    print("Residual route tables to review after closure")
    print("=" * 80)
    route_tables = route_tables_data.get("TransitRouterRouteTables", {}).get("TransitRouterRouteTable", [])
    if route_tables:
        print("\n{:<30} {:<20} {:<15}".format("Route table ID", "Related resource", "Status"))
        print("-" * 65)
        for route_table in route_tables:
            route_table_id = route_table.get("TransitRouterRouteTableId", "Unknown")
            print("{:<30} {:<20} {:<15}".format(route_table_id, "CFW related", "empty after closure"))
        print(f"\n{len(route_tables)} route tables should be reviewed after closure.")
    else:
        print("\nNo related route table information was found.")

    print("\n" + "=" * 80)
    print("Manual cleanup guidance")
    print("=" * 80)
    print("1. After closure, confirm that all business traffic has switched to the target route table.")
    print("2. In the CEN console, review residual empty route tables and delete only after manual confirmation.")
    print("3. Verify that no residual empty route table remains in CEN.")
    print("4. Review CEN billing to confirm that no unnecessary resource charge remains.")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Auto-drainage rollback: python3 analyze_routes.py auto_rollback <cfw_routes.json> <rollback_routes.json>")
        print("  Manual-drainage rollback: python3 analyze_routes.py manual_rollback <current_routes.json> <target_routes.json>")
        print("  Route revoke: python3 analyze_routes.py route_revoke <route_tables_info.json>")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "auto_rollback" and len(sys.argv) == 4:
        analyze_routes_auto_rollback(sys.argv[2], sys.argv[3])
    elif mode == "manual_rollback" and len(sys.argv) == 4:
        analyze_routes_manual_rollback(sys.argv[2], sys.argv[3])
    elif mode == "route_revoke" and len(sys.argv) == 3:
        analyze_route_revoke(sys.argv[2])
    else:
        print("Error: invalid arguments")
        print("\nUsage:")
        print("  Auto-drainage rollback: python3 analyze_routes.py auto_rollback <cfw_routes.json> <rollback_routes.json>")
        print("  Manual-drainage rollback: python3 analyze_routes.py manual_rollback <current_routes.json> <target_routes.json>")
        print("  Route revoke: python3 analyze_routes.py route_revoke <route_tables_info.json>")
        sys.exit(1)


if __name__ == "__main__":
    main()
