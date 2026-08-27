#!/usr/bin/env bash
# 06_cedar_setup.sh — create the Group D demo policies (tool-level permit +
# parameter-level `when` condition) in the user's policy set via the
# AgentIdentity API. Policy set binding to the tool happens in the console.
#
# Expects in state: E2E_POLICY_SET (default e2e-policy), E2E_MCP_TOOL (the
# hosted MCP tool name), E2E_USER_SUB (the OIDC user the IdP issues tokens
# for, e.g. testuser).
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

load_e2e_env
ACCOUNT_ID="${ACCOUNT_ID:?run 00_detect_env.sh first}"
POLICY_SET="${E2E_POLICY_SET:-e2e-policy}"
MCP_TOOL="${E2E_MCP_TOOL:?set E2E_MCP_TOOL (hosted MCP tool name)}"
USER_SUB="${E2E_USER_SUB:?set E2E_USER_SUB (OIDC user subject, e.g. testuser)}"
save_kv E2E_POLICY_SET "$POLICY_SET"

RESOURCE="acs:agentrun:${AGENTRUN_REGION}:${ACCOUNT_ID}:workspaces/system-default-workspace-${ACCOUNT_ID}/tools/${MCP_TOOL}"

py_sdk /dev/stdin "$POLICY_SET" "$MCP_TOOL" "$USER_SUB" "$RESOURCE" <<'PYEOF'
import sys
from alibabacloud_agentidentity20250901.client import Client
from alibabacloud_agentidentity20250901 import models as m
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient
import os

policy_set, tool, user, resource = sys.argv[1:5]
region = os.environ.get("E2E_REGION", "cn-hangzhou")
c = Client(om.Config(credential=CredClient(), region_id=region,
                     endpoint=f"agentidentity.{region}.aliyuncs.com",
                     user_agent=os.environ.get("SKILL_UA", "")))

# ensure the policy set exists (idempotent)
try:
    c.create_policy_set(m.CreatePolicySetRequest(policy_set_name=policy_set))
    print("[OK] policy set created:", policy_set)
except Exception as e:
    if "Exist" in str(e) or "exist" in str(e):
        print("[SKIP] policy set exists:", policy_set)
    else:
        raise

subtool = os.environ.get("E2E_MCP_SUBTOOL", "AlibabaCloud___SearchApis")
param = os.environ.get("E2E_CEDAR_PARAM", "prompt")
needle = os.environ.get("E2E_CEDAR_NEEDLE", "ECS")
# Demo stages — the two policies must NOT coexist: multiple permits combine
# with OR, so an unconditional permit voids the `when` condition of the
# parameter-level one. Stage "tool": partial-evaluation demo only. Stage
# "param": replaces the tool-level policy with the `when`-conditioned one.
stage = os.environ.get("E2E_CEDAR_STAGE", "tool")
action = f"mcp-servers.{tool}.{subtool}"

if stage == "param":
    policies = {
        "e2e-permit-param": (
            f'permit(principal==AgentIdentity::OAuthUser::"{user}",'
            f'action in [AgentRun::Action::"{action}"],'
            f'resource==AgentRun::MCPServer::"{resource}")'
            f'when{{context.input.{param} like "*{needle}*"}};'
        ),
    }
else:
    policies = {
        "e2e-permit-tool": (
            f'permit(principal==AgentIdentity::OAuthUser::"{user}",'
            f'action in [AgentRun::Action::"{action}"],'
            f'resource==AgentRun::MCPServer::"{resource}");'
        ),
    }

# always remove the OTHER stage's policy first (OR-semantics guard)
for stale in ("e2e-permit-tool", "e2e-permit-param"):
    if stale not in policies:
        try:
            c.delete_policy(m.DeletePolicyRequest(policy_set_name=policy_set, policy_name=stale))
            print("[OK] removed stale policy:", stale)
        except Exception:
            pass

for name, statement in policies.items():
    try:
        c.delete_policy(m.DeletePolicyRequest(policy_set_name=policy_set, policy_name=name))
    except Exception:
        pass
    c.create_policy(m.CreatePolicyRequest(
        policy_set_name=policy_set, policy_name=name,
        definition=m.Definition(cedar=m.DefinitionCedar(statement=statement))))
    print("[OK] policy created:", name)
print("NEXT: bind the policy set to the MCP tool in the AgentIdentity console,")
print("      then run the Group D cases in references/testing-checklist.md.")
PYEOF
