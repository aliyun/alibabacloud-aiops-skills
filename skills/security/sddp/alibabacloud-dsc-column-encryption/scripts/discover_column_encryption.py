#!/usr/bin/env python3
"""Bounded AgentHub read-only discovery. No credential setup or cloud writes."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid

import query_column_encryption as query
from aliyun_cli import build_client, resolve_profile, safe_error


ACTIONS = frozenset({"ListRegions", "ListTemplates", "ListDataMaskingInstances",
    "CheckDataMaskingInstance", "GetInstanceAttribute", "ListDataMaskingEncryptionAlgorithms",
    "ListDataAssetAccounts", "ListDataSources", "ListTables", "ListDataMaskingColumns"})
COMMANDS = frozenset({"regions", "templates", "instances", "check-instance",
    "instance-attribute", "algorithms", "accounts", "databases", "tables", "masking-columns"})
# Only observed eligibility rejections are safe to skip. Unknown business errors
# may be authorization/system failures and must stop instead of hiding them.
INELIGIBLE_CODES = frozenset({"data_masking_pg_engine_version_not_support",
                             "data_masking_instance_type_not_support"})


class BudgetExpired(Exception):
    pass


class ProbeError(Exception):
    pass


class BudgetClient:
    """Guard every RPC (including pagination), retain timing and real responses."""
    def __init__(self, client, deadline, clock=time.monotonic):
        self.client, self.deadline, self.clock = client, deadline, clock
        self.records = []

    def call(self, region, product, version, action, params):
        if product != "sddp" or version != "2026-01-20" or action not in ACTIONS:
            raise ProbeError("Action outside read-only discovery allowlist")
        start = self.clock()
        if start >= self.deadline:
            raise BudgetExpired("RPC budget exhausted; no new request submitted")
        record = {"RegionId": region, "Action": action, "Parameters": dict(params)}
        self.records.append(record)
        try:
            response = self.client.call(region, product, version, action, params)
            record["Response"] = response
            if not isinstance(response, dict) or response.get("Error") or response.get("Success") is False:
                raise ProbeError("API returned an error response")
            code = response.get("ErrorCode")
            if action != "CheckDataMaskingInstance" and code not in (None, "", "Success"):
                raise ProbeError("API returned a business error")
            if action == "CheckDataMaskingInstance" and (not isinstance(code, str) or not code):
                raise ProbeError("Eligibility response missing ErrorCode")
            if action == "CheckDataMaskingInstance" and code != "Success" and code not in INELIGIBLE_CODES:
                raise ProbeError("Unrecognized eligibility error; inspect saved response")
            return response
        except Exception as exc:
            record["Error"] = safe_error(exc)
            raise
        finally:
            record["DurationSeconds"] = round(self.clock() - start, 3)


def required(item, key):
    value = item.get(key)
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).strip():
        raise ProbeError("Response missing " + key)
    return str(value)


def rows(response, key="Items"):
    value = response.get(key)
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise ProbeError("Response missing valid " + key)
    return value


class Discovery:
    def __init__(self, client):
        self.client = client
        self.results = []
        self.report = {"Status": "DISCOVERY_INCOMPLETE", "Regions": [], "Checked": [],
                       "DeepProbes": [], "Candidates": [], "InstanceCount": 0}

    def ask(self, command, *args, paged=False):
        if command not in COMMANDS:
            raise ProbeError("Unsupported query command")
        argv = [command, *map(str, args), "--profile", "default"]
        if paged:
            argv += ["--all-pages"]
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                parsed = query.build_parser().parse_args(argv)
        except SystemExit:
            raise ProbeError("Returned resource fields are invalid for " + command) from None
        result = query.run_command(self.client, parsed)
        self.results.append({"Command": argv, "Result": result})
        if paged and (result.get("PaginationComplete") is not True
                      or result.get("PaginationTruncated") or result.get("PaginationStalled")):
            raise ProbeError("Incomplete pagination: " + command)
        return result

    def deep_probe(self, region, template, instance):
        iid, product = required(instance, "InstanceId"), required(instance, "ProductCode")
        identity = ["--region-id", region, "--product-code", product, "--instance-id", iid]
        scope = {"RegionId": region, "InstanceId": iid, "ProductCode": product,
                 "Complete": False, "Tables": []}
        self.report["DeepProbes"].append(scope)
        scope["Attribute"] = self.ask("instance-attribute", *identity)
        engine = required(instance, "EngineType")
        scope["EngineType"] = engine
        scope["Algorithms"] = self.ask("algorithms", *identity)
        scope["Accounts"] = self.ask("accounts", *identity, paged=True)
        databases = rows(self.ask("databases", *identity, paged=True))
        scope["DatabaseCount"] = len(databases)
        scope["DatabaseLimit"] = 3
        for db in databases[:3]:
            name = required(db, "DbName")
            table_args = [*identity, "--template-id", template, "--db-name", name]
            tables = rows(self.ask("tables", *table_args, paged=True))
            for table in tables[:3]:
                table_name = required(table, "Name")
                columns = rows(self.ask("masking-columns", *table_args, "--table-name", table_name,
                    "--engine-type", engine, "--masking-status", "NotEncrypted", paged=True))
                scope["Tables"].append({"Database": name, "Table": table_name,
                    "TableCount": len(tables), "TableLimit": 3, "ColumnCount": len(columns)})
                for column in columns:
                    if column.get("MaskingStatus") != "NotEncrypted":
                        raise ProbeError("Column status conflicts with NotEncrypted filter")
                    required(column, "Name")
                for column in columns[:3]:
                    self.report["Candidates"].append({"RegionId": region, "InstanceId": iid,
                        "ProductCode": product, "EngineType": engine, "Database": name,
                        "Table": table_name, "Column": column["Name"], "Status": "NotEncrypted"})
                if self.report["Candidates"]:
                    scope["Complete"] = True
                    return
        scope["Complete"] = True

    def run(self):
        try:
            regions = list(dict.fromkeys(required(r, "RegionId") for r in rows(self.ask("regions"), "RegionList")))
            templates = rows(self.ask("templates", paged=True))
            if not templates:
                raise ProbeError("No template available")
            template = required(templates[0], "Id")
            self.report["TemplateId"] = template
            ordered = [r for r in ("cn-zhangjiakou", "cn-hangzhou") if r in regions]
            ordered += [r for r in regions if r not in ordered]
            self.report["AvailableRegions"] = ordered
            seen = set()
            stop = "region limit or available regions exhausted"
            for region in ordered[:3]:
                instances = rows(self.ask("instances", "--region-id", region,
                    "--template-id", template, paged=True))
                self.report["Regions"].append(region)
                self.report["InstanceCount"] += len(instances)
                for instance in instances:
                    iid, product = required(instance, "InstanceId"), required(instance, "ProductCode")
                    key = (region, product, iid)
                    if key in seen:
                        continue
                    seen.add(key)
                    check = self.ask("check-instance", "--region-id", region,
                        "--product-code", product, "--instance-id", iid)
                    self.report["Checked"].append({"RegionId": region, "InstanceId": iid,
                        "ProductCode": product, "ErrorCode": required(check, "ErrorCode")})
                    if check["ErrorCode"] == "Success":
                        # Probe as soon as eligible, rather than enumerating all 12 first.
                        self.deep_probe(region, template, instance)
                    if self.report["Candidates"]:
                        stop = "candidate found"
                        break
                    if len(self.report["DeepProbes"]) >= 2 or len(seen) >= 12:
                        stop = "bounded instance/deep-probe limit reached"
                        break
                if self.report["Candidates"] or len(self.report["DeepProbes"]) >= 2 or len(seen) >= 12:
                    break
            self.report["StopReason"] = stop
            self.report["Status"] = "LIVE_DISCOVERY_PASS" if seen else "NO_INSTANCE_IN_CHECKED_SCOPE"
        except BudgetExpired:
            self.report["StopReason"] = "RPC budget exhausted; remaining probe incomplete"
        except Exception as exc:
            self.report.update(Status="QUERY_FAILED", StopReason=safe_error(exc))
        return self.report


def summary(report, evidence):
    lines = [report["Status"]]
    if report["Status"] == "LIVE_DISCOVERY_PASS":
        lines += ["InstancePaginationComplete=true", "CandidateFound=" + str(bool(report["Candidates"])).lower()]
    lines += ["StopReason=" + report.get("StopReason", ""),
              "Regions=" + ",".join(report["Regions"]),
              "TemplateId=" + str(report.get("TemplateId", "unavailable")),
              "CheckedInstances=" + str(len(report["Checked"])),
              "ListedInstances=" + str(report["InstanceCount"]),
              "DeepProbes=" + str(len(report["DeepProbes"])),
              "Candidates=" + json.dumps(report["Candidates"], ensure_ascii=False),
              "Evidence=" + str(evidence),
              "Scope=bounded metadata only; unvisited regions/instances/tables remain unverified",
              "TemplateCaveat=table/column queries may fall back to 98; attribution not verified",
              "Writes=none; discovery does not authorize writes"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["default"], required=True)
    parser.add_argument("--expected-role-arn", required=True)
    parser.add_argument("--budget-seconds", type=int, choices=range(1, 481), default=300, metavar="1..480")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args(argv)
    start = time.monotonic()
    try:
        if sys.version_info < (3, 10):
            raise ProbeError("Python >=3.10 required")
        if not re.fullmatch(r"acs:ram::[0-9]+:role/[A-Za-z0-9._/-]+", args.expected_role_arn):
            raise ProbeError("Invalid expected role ARN")
        if os.environ.get("EVAL_ROLE_ARN") != args.expected_role_arn:
            raise ProbeError("Trusted platform role binding absent or mismatched; do not set it manually")
        profile = resolve_profile(args.profile)
        if profile.mode not in {"StsToken", "RamRoleArn"}:
            raise ProbeError("AgentHub discovery requires StsToken or RamRoleArn")
        os.environ["ALIBABA_CLOUD_SKILL_SESSION_ID"] = uuid.uuid4().hex
        args.output_dir.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="discovery-", dir=args.output_dir))
        client = BudgetClient(build_client(profile, query.CONTROL_PLANE_REGION), start + args.budget_seconds)
    except Exception as exc:
        print("ENVIRONMENT_BLOCKED\n" + safe_error(exc))
        return 1
    probe = Discovery(client)
    report = probe.run()
    evidence = directory / "evidence.json"
    payload = {"Report": report, "Queries": probe.results, "Calls": client.records,
               "SessionId": os.environ["ALIBABA_CLOUD_SKILL_SESSION_ID"],
               "ElapsedSeconds": round(time.monotonic() - start, 3)}
    try:
        evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        output = summary(report, evidence)
        (directory / "summary.txt").write_text(output, encoding="utf-8")
    except OSError:
        print("QUERY_FAILED\nEvidence could not be saved; no success claimed")
        return 1
    print(output, end="")
    return 0 if report["Status"] == "LIVE_DISCOVERY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
