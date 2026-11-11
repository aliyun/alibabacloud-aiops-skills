#!/usr/bin/env bash
# 05_attach_role_policy.sh — attach AliyunOSSReadOnlyAccess to the role of
# the workload identity that the Runtime deployment AUTO-created (platform-
# managed, name agentrun-<runtime-id>). Finds the role by matching the
# SourceAgentArn against the runtime name; no console needed.
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

load_e2e_env
ACCOUNT_ID="${ACCOUNT_ID:?run 00_detect_env.sh first}"
RUNTIME_NAME="${E2E_RUNTIME_NAME:?run 04_reachability.sh first}"

ROLE=$(py_sdk /dev/stdin "$ACCOUNT_ID" "$AGENTRUN_REGION" "$RUNTIME_NAME" <<'PYEOF'
import os
import sys
from alibabacloud_agentidentity20250901.client import Client
from alibabacloud_agentidentity20250901 import models as m
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient

account, region, runtime_name = sys.argv[1:4]
c = Client(om.Config(credential=CredClient(), region_id=region,
                     endpoint=f"agentidentity.{region}.aliyuncs.com",
                     user_agent=os.environ.get("SKILL_UA", "")))
roles = []
next_token = None
seen_tokens = set()
while True:
    resp = c.list_workload_identities(m.ListWorkloadIdentitiesRequest(next_token=next_token))
    for wi in resp.body.workload_identities or []:
        d = wi.to_map()
        source = (d.get("SourceAgentArn") or "").split(":", 4)
        if len(source) != 5 or source[:4] != ["acs", "agentrun", region, account]:
            continue
        resource = source[4].split("/")
        if len(resource) < 2 or resource[-2] != "runtimes" or resource[-1] != runtime_name:
            continue
        role = (d.get("RoleArn") or "").split(":", 4)
        if (len(role) != 5 or role[:4] != ["acs", "ram", "", account]
                or not role[4].startswith("role/") or not role[4][5:]
                or "/" in role[4][5:]):
            sys.exit("[FAIL] matched workload identity has an invalid RAM role; no policy was attached")
        roles.append(role[4][5:])
    next_token = resp.body.next_token
    if not next_token:
        break
    if next_token in seen_tokens:
        sys.exit("[FAIL] workload identity pagination repeated a token; no policy was attached")
    seen_tokens.add(next_token)

if len(roles) != 1:
    sys.exit(f"[FAIL] expected one workload identity for this runtime, found {len(roles)}; no policy was attached")
print(roles[0])
PYEOF
)

[ -n "$ROLE" ] || fail "no auto-created workload identity found for runtime ${RUNTIME_NAME} — was the runtime deployed with AgentIdentity credential config?"
save_kv E2E_WI_ROLE "$ROLE"
log_ok "runtime workload-identity role: $ROLE"

POLICIES=$("$ALIYUN" ram list-policies-for-role \
  --role-name "$ROLE" --user-agent "$(ua_string)") \
  || fail "cannot read attached policies for $ROLE; no policy was attached"
POLICY_STATUS=$(printf '%s' "$POLICIES" | python3 -c '
import json, sys
policies = json.load(sys.stdin)["Policies"]["Policy"]
if not isinstance(policies, list):
    sys.exit("[FAIL] invalid ListPoliciesForRole response")
print("attached" if any(p["PolicyName"] == "AliyunOSSReadOnlyAccess"
                        and p["PolicyType"] == "System" for p in policies) else "missing")
') || fail "cannot verify attached policies for $ROLE; no policy was attached"
if [ "$POLICY_STATUS" = "attached" ]; then
  log_skip "AliyunOSSReadOnlyAccess is already attached to $ROLE"
  exit 0
fi

"$ALIYUN" ram attach-policy-to-role \
  --policy-type System --policy-name AliyunOSSReadOnlyAccess \
  --role-name "$ROLE" --user-agent "$(ua_string)" >/dev/null \
  && log_ok "attached AliyunOSSReadOnlyAccess to $ROLE" \
  || fail "failed to attach AliyunOSSReadOnlyAccess to $ROLE; check the RAM error above"
