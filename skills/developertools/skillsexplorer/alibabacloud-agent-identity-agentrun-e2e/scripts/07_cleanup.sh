#!/usr/bin/env bash
# 07_cleanup.sh — delete resources created by this skill run via API, and
# print the console checklist for everything that cannot be deleted via API.
# Never touches user-provided resources (IdP, RAM app, model service).
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

load_e2e_env
# Cleanup must reach the same Python env the other phases used. py_sdk does
# this too, but it only runs when a policy set exists — the OSS block below
# would otherwise fall back to whatever python3 is on PATH. A warning, not a
# hard failure: cleanup should still attempt what it can.
init_conda >/dev/null 2>&1 || log_warn "conda env unavailable — using the python3 on PATH"
POLICY_SET="${E2E_POLICY_SET:-}"
OSS_BUCKET="${E2E_OSS_BUCKET:-}"
OSS_KEY="${E2E_OSS_KEY:-hello.txt}"

echo "=== API cleanup ==="

# 1. Cedar policies + policy set (if this skill created them)
if [ -n "$POLICY_SET" ]; then
  py_sdk /dev/stdin "$POLICY_SET" <<'PYEOF' || log_warn "policy cleanup failed (continue)"
import sys
from alibabacloud_agentidentity20250901.client import Client
from alibabacloud_agentidentity20250901 import models as m
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient
import os

policy_set = sys.argv[1]
region = os.environ.get("E2E_REGION", "cn-hangzhou")
c = Client(om.Config(credential=CredClient(), region_id=region,
                     endpoint=f"agentidentity.{region}.aliyuncs.com",
                     user_agent=os.environ.get("SKILL_UA", "")))
for name in ("e2e-permit-tool", "e2e-permit-param"):
    try:
        c.delete_policy(m.DeletePolicyRequest(policy_set_name=policy_set, policy_name=name))
        print("[OK] policy deleted:", name)
    except Exception:
        pass
try:
    c.delete_policy_set(m.DeletePolicySetRequest(policy_set_name=policy_set))
    print("[OK] policy set deleted:", policy_set)
except Exception as e:
    print("[SKIP] policy set:", str(e)[:80])
PYEOF
fi

# 2. OSS test file + bucket (skill-created)
if [ -n "$OSS_BUCKET" ]; then
  ensure_oss_deps
  # Provider preamble prepended outside the quoted heredoc (see 02_oss_testfile.sh).
  export SKILL_UA
  SKILL_UA=$(ua_string)
  {
    oss_provider_snippet
    cat <<'PYEOF'

bucket_name = os.environ["OSS_BUCKET"]
key = os.environ["OSS_KEY"]
region = os.environ["E2E_OSS_REGION"]
bucket = oss2.Bucket(oss_auth(), f"https://oss-{region}.aliyuncs.com", bucket_name,
                     region=region, app_name=OSS_UA)
try:
    bucket.delete_object(key)
    print("[OK] object deleted:", key)
except Exception:
    pass
try:
    bucket.delete_bucket()
    print("[OK] bucket deleted:", bucket_name)
except Exception as e:
    print("[SKIP] bucket delete:", str(e)[:80], "(empty it in console if kept)")
PYEOF
  } | OSS_BUCKET="$OSS_BUCKET" OSS_KEY="$OSS_KEY" E2E_OSS_REGION="$E2E_OSS_REGION" \
      python3 - || log_warn "OSS cleanup failed (continue)"
fi

echo
echo "=== Console cleanup checklist (cannot be deleted via API) ==="
cat <<'EOF'
1. AgentRun console → Agent 运行时 → delete the test runtime (agent-*)
2. AgentRun console → 工具与Skills → delete the test MCP tool(s)
3. AgentIdentity console → 凭证提供商 → delete test providers (API-key / OAuth2)
   — only those created for this run; keep user-provided ones
4. AgentIdentity console → 身份提供商 → keep (user-provided) or delete if test-only
5. Created DingTalk docs (Group E) are user content — keep or delete in DingTalk
EOF
log_ok "cleanup done"
