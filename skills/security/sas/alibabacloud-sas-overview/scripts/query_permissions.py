#!/usr/bin/env python3
"""Print only the RAM actions for explicitly selected overview items (offline)."""
import argparse
import json

SAS = "yundun-sas:"
SCOPES = {
    "score": [SAS + "DescribeSecureSuggestion"],
    "vul-fixes": [SAS + "DescribeVulFixStatistics"],
    "baseline": [SAS + "GetCheckRiskStatistics"],
    "handled-alerts": [SAS + "GetDefenceCount"],
    "service": [SAS + "DescribeVersionConfig"],
    "hosts": [SAS + "DescribeCloudCenterInstances"],
    "uninstalled": [SAS + "ListUninstallAegisMachines"],
    "governance": [SAS + "DescribeSecureSuggestion"],
    "security-response": [SAS + "DescribeSecureSuggestion"],
    "waf": ["yundun-waf:DescribeInstance", "yundun-waf:DescribeFlowChart"],
    "host-risk": [SAS + "DescribeCloudCenterInstances", SAS + "DescribeFieldStatistics"],
    "container-risk": [SAS + "DescribeContainerFieldStatistics"],
    "cloud-risk": [SAS + "GetCloudAssetSummary"],
    "trend": [SAS + "DescribeChartData"],
    "billing-config": [SAS + "DescribeVersionConfig"],
    "bills": ["bss:QueryBill"],
}


def required_actions(items):
    if not items or any(item not in SCOPES and item != "all" for item in items):
        raise ValueError("Specify known query items; scope must not expand implicitly")
    selected = SCOPES if "all" in items else items
    return sorted({action for item in selected for action in SCOPES[item]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("items", nargs="+", choices=[*SCOPES, "all"])
    args = parser.parse_args()
    print(json.dumps({"required_actions": required_actions(args.items)}, indent=2))


if __name__ == "__main__":
    main()
