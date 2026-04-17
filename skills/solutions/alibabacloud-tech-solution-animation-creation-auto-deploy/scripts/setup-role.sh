#!/bin/bash
set -euo pipefail

# Step 4 pre-requisite: Get UID and check/update role trust policy
# Optional env var: MY_UID (auto-fetched if not set)

REGION="cn-hangzhou"
ROLE_NAME="aliyundevscustomrole"
TRUST_POLICY='{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":["devs.aliyuncs.com","fc.aliyuncs.com"]}}],"Version":"1"}'

# Auto-fetch MY_UID
if [ -z "${MY_UID:-}" ]; then
  MY_UID=$(aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['AccountId'])")
fi
export MY_UID
echo "UID: $MY_UID"

# Check if role exists; create if not
ROLE_POLICY=$(aliyun ram get-role --role-name "$ROLE_NAME" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['Role']['AssumeRolePolicyDocument'])" 2>/dev/null || echo "")
if [ -z "$ROLE_POLICY" ]; then
  echo "Role $ROLE_NAME not found, creating..."
  aliyun ram create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST_POLICY" --description "Role for Devs and FC services" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
  echo "Role created."
elif echo "$ROLE_POLICY" | grep -q "fc.aliyuncs.com"; then
  echo "Role trust policy already includes fc.aliyuncs.com, skipping update"
else
  echo "Updating role trust policy to include fc.aliyuncs.com..."
  aliyun ram update-role --role-name "$ROLE_NAME" --new-assume-role-policy-document "$TRUST_POLICY" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
fi
