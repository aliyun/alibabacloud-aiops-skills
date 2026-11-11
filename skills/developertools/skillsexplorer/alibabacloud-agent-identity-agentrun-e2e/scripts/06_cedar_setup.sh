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

init_conda || fail "run 00_detect_env.sh first"
load_e2e_env
ACCOUNT_ID="${ACCOUNT_ID:?run 00_detect_env.sh first}"
POLICY_SET="${E2E_POLICY_SET:-e2e-policy}"
MCP_TOOL="${E2E_MCP_TOOL:?set E2E_MCP_TOOL (hosted MCP tool name)}"
USER_SUB="${E2E_USER_SUB:?set E2E_USER_SUB (OIDC user subject, e.g. testuser)}"
E2E_MCP_SUBTOOL="${E2E_MCP_SUBTOOL-AlibabaCloud___SearchApis}"
E2E_CEDAR_PARAM="${E2E_CEDAR_PARAM-prompt}"
E2E_CEDAR_NEEDLE="${E2E_CEDAR_NEEDLE-ECS}"
E2E_CEDAR_STAGE="${E2E_CEDAR_STAGE:-tool}"
case "$E2E_CEDAR_STAGE" in tool|param) ;; *) fail "E2E_CEDAR_STAGE must be tool or param" ;; esac
export E2E_CEDAR_STAGE E2E_MCP_SUBTOOL E2E_CEDAR_PARAM E2E_CEDAR_NEEDLE
save_kv E2E_POLICY_SET "$POLICY_SET"
for key in AGENTRUN_REGION E2E_MCP_TOOL E2E_USER_SUB E2E_MCP_SUBTOOL E2E_CEDAR_PARAM E2E_CEDAR_NEEDLE; do
  save_kv "$key" "${!key}"
done
prepare_created_state

RESOURCE="acs:agentrun:${AGENTRUN_REGION}:${ACCOUNT_ID}:workspaces/system-default-workspace-${ACCOUNT_ID}/tools/${MCP_TOOL}"

{
  created_state_snippet
  cat <<'PYEOF'
import sys
from alibabacloud_agentidentity20250901.client import Client
from alibabacloud_agentidentity20250901 import models as m
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient
import os

policy_set, tool, user, resource = sys.argv[1:5]
region = os.environ["AGENTRUN_REGION"]
c = Client(om.Config(credential=CredClient(), region_id=region,
                     endpoint=f"agentidentity.{region}.aliyuncs.com",
                     user_agent=os.environ.get("SKILL_UA", "")))

record = _created.get("E2E_CREATED_CEDAR")
if record and (record[1:3] != [region, policy_set]
               or record[3] not in ("created", "reused")
               or record[4] not in ("none", "tool", "param")):
    raise RuntimeError("A different or invalid Cedar test record is awaiting cleanup")
try:
    c.get_policy_set(m.GetPolicySetRequest(policy_set_name=policy_set))
except Exception as error:
    if getattr(error, "code", None) != "EntityNotExists.PolicySet":
        raise
    c.create_policy_set(m.CreatePolicySetRequest(policy_set_name=policy_set))
    save_created("E2E_CREATED_CEDAR", region, policy_set, "created", "none")
    record = _created["E2E_CREATED_CEDAR"]
    print("[OK] policy set created:", policy_set)

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

# Other permits would invalidate the parameter-denial test.
existing = []
next_token = None
while True:
    body = c.list_policies(m.ListPoliciesRequest(policy_set_name=policy_set,
                                               next_token=next_token)).body
    for policy in body.policies or []:
        if not record or record[4] == "none" or policy.policy_name != "e2e-permit-" + record[4]:
            raise RuntimeError("Choose an empty test policy set; unrelated policies will not be changed")
        existing.append(policy.policy_name)
    next_token = body.next_token
    if not next_token:
        break
ownership = record[3] if record else "reused"
for name in existing:
    c.delete_policy(m.DeletePolicyRequest(policy_set_name=policy_set, policy_name=name))
save_created("E2E_CREATED_CEDAR", region, policy_set, ownership, "none")

for name, statement in policies.items():
    c.create_policy(m.CreatePolicyRequest(
        policy_set_name=policy_set, policy_name=name,
        definition=m.Definition(cedar=m.DefinitionCedar(statement=statement))))
    save_created("E2E_CREATED_CEDAR", region, policy_set, ownership, stage)
    print("[OK] policy created:", name)
print("NEXT: bind the policy set to the MCP tool in the AgentIdentity console,")
print("      then run the Group D cases in references/testing-checklist.md.")
PYEOF
} | py_sdk /dev/stdin "$POLICY_SET" "$MCP_TOOL" "$USER_SUB" "$RESOURCE"
