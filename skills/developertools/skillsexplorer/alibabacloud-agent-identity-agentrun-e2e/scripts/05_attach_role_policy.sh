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

ROLE=$(py_sdk /dev/stdin <<PYEOF
import json, os
from alibabacloud_agentidentity20250901.client import Client
from alibabacloud_agentidentity20250901 import models as m
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient

region = "${AGENTRUN_REGION}"
c = Client(om.Config(credential=CredClient(), region_id=region,
                     endpoint=f"agentidentity.{region}.aliyuncs.com",
                     user_agent=os.environ.get("SKILL_UA", "")))
resp = c.list_workload_identities(m.ListWorkloadIdentitiesRequest())
for wi in (resp.body.workload_identities or []):
    d = wi.to_map()
    if "${RUNTIME_NAME}" in (d.get("SourceAgentArn") or ""):
        role = (d.get("RoleArn") or "").split("/")[-1]
        print(role)
        break
PYEOF
)

[ -n "$ROLE" ] || fail "no auto-created workload identity found for runtime ${RUNTIME_NAME} — was the runtime deployed with AgentIdentity credential config?"
save_kv E2E_WI_ROLE "$ROLE"
log_ok "runtime workload-identity role: $ROLE"

"$ALIYUN" ram attach-policy-to-role \
  --policy-type System --policy-name AliyunOSSReadOnlyAccess \
  --role-name "$ROLE" --user-agent "$(ua_string)" >/dev/null \
  && log_ok "attached AliyunOSSReadOnlyAccess to $ROLE" \
  || log_skip "attach returned non-zero (possibly already attached) — verify in RAM console if Group C OSS reads fail"
