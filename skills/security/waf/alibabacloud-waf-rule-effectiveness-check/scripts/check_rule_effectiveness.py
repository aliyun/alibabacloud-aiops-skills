#!/usr/bin/env python3
"""
WAF Custom Rule Effectiveness Checker (read-only)

Statically verifies the "rule -> template -> resource" binding chain for a WAF 3.0
custom defense rule (DefenseOrigin=custom) against a given defense resource
(matched_host), and reports the first failing element of the effectiveness quad:

  1. rule Status == 1
  2. resource (or its resource group) is bound to the rule's template
  3. template TemplateStatus == 1
  4. action is blocking, not observe/monitor (a monitored rule matches but does
     not block the request -- the top root cause of "rule hit but nothing blocked")

Plus auxiliary gates: ResourceStatus == active and template binding quota.
Scope: custom rules only. Whitelist / built-in (system) rules are out of scope.

Note: when the action field cannot be parsed out of Config, element 4 is reported
as an undetermined note instead of a pass -- never treat "unparsed" as "blocking".

Usage:
    # Check a rule by ID against a defense resource (inject session-id per SKILL.md Observability)
    SKILL_SESSION_ID=<session-id> python3 check_rule_effectiveness.py --rule-id 123456 --resource www.example.com-waf

    # Check by rule name (fuzzy)
    SKILL_SESSION_ID=<session-id> python3 check_rule_effectiveness.py --rule-name "acl_ops" --resource www.example.com-waf

    # JSON output
    SKILL_SESSION_ID=<session-id> python3 check_rule_effectiveness.py --rule-id 123456 --resource www.example.com-waf --json

Exit codes:
    0: all checks passed (rule is effective on the resource)
    1: some element failed (first failing element reported)
    2: query error / rule or resource not found / out-of-scope rule type
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
import time

SKILL_NAME = "alibabacloud-waf-rule-effectiveness-check"
STAT_SCENES = {"cc", "antiscan_highfreq", "antiscan_dirscan", "antiscan_scantools"}
THROTTLE_SLEEP = 0.3
# Observe/monitor-style action values: the rule matches and is logged, but the
# request is NOT blocked. Treated as element 4 failure (root cause on its own).
OBSERVE_ACTIONS = {"monitor", "observe", "watch", "log", "alarm", "warn"}


def run_aliyun(args, session_id):
    """Run an aliyun CLI command and return parsed JSON."""
    cmd = ["aliyun", "waf-openapi"] + args + [
        "--user-agent", f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip())
    return json.loads(proc.stdout or "{}")


def throttled():
    time.sleep(THROTTLE_SLEEP)


def get_instance(region, session_id):
    return run_aliyun(["describe-instance", "--biz-region-id", region], session_id)


def find_rule(instance_id, region, rule_id, rule_name, session_id):
    """Locate a custom defense rule by ID (exact) or name (fuzzy)."""
    query = {"ruleId": int(rule_id)} if rule_id else {"nameLike": rule_name}
    data = run_aliyun(["describe-defense-rules", "--biz-region-id", region,
                       "--instance-id", instance_id,
                       "--query", json.dumps(query)], session_id)
    rules = data.get("Rules") or []
    return rules[0] if rules else None


def get_template(instance_id, region, template_id, session_id):
    data = run_aliyun(["describe-defense-template", "--biz-region-id", region,
                       "--instance-id", instance_id, "--template-id", str(template_id)], session_id)
    return data.get("Template") or {}


def get_template_resources(instance_id, region, template_id, resource_type, session_id):
    """Page through DescribeTemplateResources and return the full name list."""
    names, next_token = [], None
    while True:
        args = ["describe-template-resources", "--biz-region-id", region,
                "--instance-id", instance_id, "--template-id", str(template_id),
                "--resource-type", resource_type, "--max-results", "500"]
        if next_token:
            args += ["--next-token", next_token]
        data = run_aliyun(args, session_id)
        names.extend(data.get("Resources") or [])
        next_token = data.get("NextToken")
        if not next_token:
            break
        throttled()
    return names


def get_resource(instance_id, region, resource, session_id):
    data = run_aliyun(["describe-defense-resource", "--biz-region-id", region,
                       "--instance-id", instance_id, "--resource", resource], session_id)
    return data.get("Resource") or {}


def is_stat_rule(rule):
    scene = rule.get("DefenseScene", "")
    if scene in STAT_SCENES:
        return True
    if scene == "custom_acl":
        try:
            cfg = json.loads(rule.get("Config") or "{}")
        except (ValueError, TypeError):
            return False
        return str(cfg.get("ccStatus", "0")) == "1" or "ratelimit" in json.dumps(cfg).lower()
    return False


def extract_action(rule):
    """Pull the disposal action out of the rule Config.

    Returns the raw action value, or None when it cannot be determined --
    callers must NOT read None as "blocking".
    """
    try:
        cfg = json.loads(rule.get("Config") or "{}")
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):
        return None
    for key in ("action", "Action", "actionType", "effectAction"):
        value = cfg.get(key)
        if isinstance(value, str) and value:
            return value
    for value in cfg.values():
        if isinstance(value, dict):
            for key in ("action", "Action"):
                nested = value.get(key)
                if isinstance(nested, str) and nested:
                    return nested
    return None


def main():
    parser = argparse.ArgumentParser(description="Read-only WAF custom rule effectiveness checker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rule-id", help="Custom defense rule ID")
    group.add_argument("--rule-name", help="Custom defense rule name keyword (fuzzy)")
    parser.add_argument("--resource", required=True, help="Defense resource (matched_host)")
    parser.add_argument("--region", default="cn-hangzhou", help="cn-hangzhou or ap-southeast-1")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    args = parser.parse_args()

    session_id = os.environ.get("SKILL_SESSION_ID", "") or secrets.token_hex(16)
    report = {"checks": [], "effective": False, "first_failure": None, "notes": []}

    try:
        # Phase 1: instance + resource
        instance = get_instance(args.region, session_id)
        instance_id = instance.get("InstanceId")
        details = instance.get("Details") or {}
        quota = details.get("DefenseObjectInTemplateMaxCount")
        if not instance_id:
            print("[ERROR] No WAF instance found in region %s" % args.region, file=sys.stderr)
            sys.exit(2)
        throttled()

        resource = get_resource(instance_id, args.region, args.resource, session_id)
        resource_status = resource.get("ResourceStatus")
        resource_group = resource.get("ResourceGroup") or ""
        if not resource:
            print(f"[ERROR] Defense resource not found: {args.resource}", file=sys.stderr)
            sys.exit(2)
        report["resource"] = {"name": args.resource, "status": resource_status,
                              "group": resource_group,
                              "acw_cookie_status": resource.get("AcwCookieStatus")}
        if resource_status != "active":
            report["notes"].append(
                f"ResourceStatus={resource_status}: resource not ready, binding may fail; "
                "wait and retry before calling it a misconfiguration")
        throttled()

        # Phase 2: locate rule (custom only)
        rule = find_rule(instance_id, args.region, args.rule_id, args.rule_name, session_id)
        if not rule:
            print("[ERROR] Rule not found. Check ID/name; whitelist rules are out of scope.",
                  file=sys.stderr)
            sys.exit(2)
        if rule.get("DefenseOrigin") != "custom":
            print(f"[ERROR] Rule {rule.get('RuleId')} is a built-in (system) rule; "
                  "this skill only checks custom rules.", file=sys.stderr)
            sys.exit(2)
        rule_id = rule.get("RuleId")
        template_id = rule.get("TemplateId")
        action = extract_action(rule)
        report["rule"] = {
            "rule_id": rule_id, "rule_name": rule.get("RuleName"),
            "status": rule.get("Status"),
            "defense_origin": rule.get("DefenseOrigin"),
            "defense_scene": rule.get("DefenseScene"),
            "template_id": template_id,
            "config": rule.get("Config"),
            "action": action,
            "is_stat_rule": is_stat_rule(rule),
        }
        throttled()

        # Phase 3: triad
        # 1) rule enabled
        rule_on = rule.get("Status") == 1
        report["checks"].append({"id": 1, "name": "rule status enabled",
                                 "passed": rule_on, "actual": f"Status={rule.get('Status')}"})

        # 2) resource bound to template (directly or via group)
        bound_single = bound_group = False
        single_names = group_names = []
        if template_id:
            single_names = get_template_resources(instance_id, args.region, template_id,
                                                  "single", session_id)
            bound_single = args.resource in single_names
            throttled()
            if not bound_single and resource_group:
                group_names = get_template_resources(instance_id, args.region, template_id,
                                                     "group", session_id)
                bound_group = resource_group in group_names
                throttled()
        bound = bound_single or bound_group
        via = "direct" if bound_single else ("via group %s" % resource_group if bound_group else "no")
        report["checks"].append({
            "id": 2, "name": "resource bound to template", "passed": bound,
            "actual": f"template={template_id}, bound={via}, "
                      f"single_count={len(single_names)}"})
        if quota is not None and len(single_names) >= quota and not bound:
            report["notes"].append(
                f"template binding count {len(single_names)} reached quota {quota} "
                f"(DefenseObjectInTemplateMaxCount); new binding will fail")

        # 3) template enabled
        template = get_template(instance_id, args.region, template_id, session_id) if template_id else {}
        tmpl_on = template.get("TemplateStatus") == 1
        report["checks"].append({"id": 3, "name": "template enabled", "passed": tmpl_on,
                                 "actual": f"TemplateStatus={template.get('TemplateStatus')}, "
                                           f"name={template.get('TemplateName')}"})

        # 4) action is blocking, not observe/monitor
        if action is None:
            report["notes"].append(
                "element 4 (action) undetermined: no action field parsed from Config -- "
                "verify manually in console/log; do NOT assume it is blocking")
        else:
            report["checks"].append({
                "id": 4, "name": "action is blocking (not observe)",
                "passed": action.lower() not in OBSERVE_ACTIONS,
                "actual": f"action={action}"})
            if action.lower() in OBSERVE_ACTIONS:
                report["notes"].append(
                    f"action={action} is observe/monitor mode: the rule matches and is logged "
                    "but does NOT block the request -- this is the root cause itself; "
                    "a 4xx/5xx seen by the customer comes from the origin server")

        report["checks"].append({"id": 5, "name": "resource initialized",
                                 "passed": resource_status == "active",
                                 "actual": f"ResourceStatus={resource_status}"})

        for check in report["checks"]:
            if not check["passed"] and not report["first_failure"]:
                report["first_failure"] = check
        report["effective"] = all(c["passed"] for c in report["checks"])

    except RuntimeError as e:
        print(f"[ERROR] aliyun CLI call failed: {e}", file=sys.stderr)
        sys.exit(2)
    except FileNotFoundError:
        print("[ERROR] aliyun CLI not found. Install it first.", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'=' * 64}")
        print("  WAF Custom Rule Effectiveness Check (read-only)")
        print(f"{'=' * 64}")
        r = report.get("rule") or {}
        print(f"  Rule: [{r.get('rule_id')}] {r.get('rule_name')} "
              f"(scene={r.get('defense_scene')}, origin={r.get('defense_origin')})")
        print(f"  Resource: {args.resource}")
        print(f"  Action: {r.get('action') or 'undetermined (verify manually)'}")
        print(f"  Stat-style rule (CC/antiscan): {'Yes' if r.get('is_stat_rule') else 'No'}")
        for check in report["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            print(f"  [{mark}] element {check['id']}: {check['name']} -- {check['actual']}")
        for note in report["notes"]:
            print(f"  [NOTE] {note}")
        if report["effective"]:
            print("  Result: EFFECTIVE -- all checked elements passed on this resource")
        else:
            f = report["first_failure"]
            print(f"  Result: NOT EFFECTIVE -- first failing element: "
                  f"#{f['id']} {f['name']} ({f['actual']})")
        print(f"{'=' * 64}\n")

    sys.exit(0 if report["effective"] else 1)


if __name__ == "__main__":
    main()
