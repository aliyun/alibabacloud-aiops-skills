#!/usr/bin/env bash
# 07_cleanup.sh — delete resources created by this skill run via API, and
# print the console checklist for resources not automated by this Skill.
# Never touches user-provided resources (IdP, RAM app, model service).
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

load_e2e_env
init_conda >/dev/null 2>&1 || log_warn "conda env unavailable — using the python3 on PATH"
cleanup_failed=0
if grep -Eq '^E2E_CREATED_(OSS_BUCKET|OSS_OBJECT|CEDAR)=.+' "$ENV_FILE" 2>/dev/null; then
  prepare_created_state
fi

echo "=== API cleanup ==="

# 1. Cedar policies + policy set (if this skill created them)
if grep -Eq '^E2E_CREATED_CEDAR=.+' "$ENV_FILE" 2>/dev/null; then
  {
    created_state_snippet
    cat <<'PYEOF'
from alibabacloud_agentidentity20250901.client import Client
from alibabacloud_agentidentity20250901 import models as m
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient

_, region, policy_set, ownership, stage = _created["E2E_CREATED_CEDAR"]
if ownership not in ("created", "reused") or stage not in ("none", "tool", "param"):
    raise RuntimeError("Invalid Cedar cleanup record")
c = Client(om.Config(credential=CredClient(), region_id=region,
                     endpoint=f"agentidentity.{region}.aliyuncs.com",
                     user_agent=os.environ.get("SKILL_UA", "")))
next_token = None
set_missing = False
while True:
    try:
        body = c.list_policy_set_attached_gateways(
            m.ListPolicySetAttachedGatewaysRequest(policy_set_name=policy_set,
                                                   next_token=next_token)).body
    except Exception as error:
        if getattr(error, "code", None) != "EntityNotExists.PolicySet":
            raise
        set_missing = True
        break
    if body.attached_gateways:
        raise RuntimeError("Restore the tool's original policy binding before cleanup")
    next_token = body.next_token
    if not next_token:
        break
if not set_missing:
    if stage != "none":
        name = "e2e-permit-" + stage
        try:
            c.delete_policy(m.DeletePolicyRequest(policy_set_name=policy_set, policy_name=name))
        except Exception as error:
            if getattr(error, "code", None) not in ("EntityNotExists.Policy", "EntityNotExists.PolicySet"):
                raise
        save_created("E2E_CREATED_CEDAR", region, policy_set, ownership, "none")
        print("[OK] policy deleted:", name)
    if ownership == "created":
        next_token = None
        while True:
            body = c.list_policies(m.ListPoliciesRequest(policy_set_name=policy_set,
                                                       next_token=next_token)).body
            if body.policies:
                raise RuntimeError("Policy set contains unrecorded policies; it was not deleted")
            next_token = body.next_token
            if not next_token:
                break
        c.delete_policy_set(m.DeletePolicySetRequest(policy_set_name=policy_set))
        print("[OK] policy set deleted:", policy_set)
save_created("E2E_CREATED_CEDAR")
PYEOF
  } | py_sdk /dev/stdin || cleanup_failed=1
fi

# 2. OSS test file + bucket (skill-created)
if grep -Eq '^E2E_CREATED_OSS_(BUCKET|OBJECT)=.+' "$ENV_FILE" 2>/dev/null; then
  if (ensure_oss_deps); then
    {
      created_state_snippet
      oss_provider_snippet
      cat <<'PYEOF'
keys = ("E2E_CREATED_OSS_OBJECT", "E2E_CREATED_OSS_BUCKET")
records = [_created[key] for key in keys if key in _created]
region, bucket_name = records[0][1:3]
if any(record[1:3] != [region, bucket_name] for record in records):
    raise RuntimeError("OSS cleanup records refer to different buckets")
bucket = oss2.Bucket(oss_auth(), f"https://oss-{region}.aliyuncs.com", bucket_name,
                     region=region, app_name=OSS_UA)
for key in keys:
    if key not in _created:
        continue
    try:
        if key == "E2E_CREATED_OSS_OBJECT":
            bucket.delete_object(_created[key][3])
        else:
            bucket.delete_bucket()
    except Exception as error:
        missing = ("NoSuchBucket", "NoSuchKey") if key == "E2E_CREATED_OSS_OBJECT" else ("NoSuchBucket",)
        if getattr(error, "code", None) not in missing:
            raise
    save_created(key)
    print("[OK] test resource deleted:", key)
PYEOF
    } | python3 - || cleanup_failed=1
  else
    cleanup_failed=1
  fi
fi

echo
echo "=== Console cleanup checklist (manual steps) ==="
cat <<'EOF'
1. AgentRun console → Agent 运行时 → delete only runtimes created for this run
   — restore and preserve reused runtimes; remove only role grants added by this run
2. AgentRun console → 工具与Skills → delete only MCP tools created for this run
   — restore and preserve reused tools
3. AgentIdentity console → 凭证提供商 → delete test providers (API-key / OAuth2)
   — only those created for this run; keep user-provided ones
4. AgentIdentity console → 身份提供商 → delete only registrations created for this run
   — keep user-provided registrations
5. Created DingTalk docs (Group E) are user content — keep or delete in DingTalk
EOF
[ "$cleanup_failed" -eq 0 ] || fail "cleanup incomplete; failed creation records were preserved"
log_ok "API cleanup completed; finish the console checklist"
