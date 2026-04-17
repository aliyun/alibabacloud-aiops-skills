#!/bin/bash
set -euo pipefail

# RAM Policy: Auto-detect identity type and attach required policies
# No env vars needed — identity info is fetched automatically

POLICIES="AliyunOSSFullAccess AliyunFCFullAccess"

IDENTITY=$(aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1)
IDENTITY_TYPE=$(echo "$IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['IdentityType'])")

if [ "$IDENTITY_TYPE" = "RAMUser" ]; then
  RAM_USER=$(echo "$IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'].split('/')[-1])")
  echo "RAM user: $RAM_USER, auto-attaching required policies..."
  for POLICY in $POLICIES; do
    aliyun ram attach-policy-to-user --policy-type System --policy-name "$POLICY" --user-name "$RAM_USER" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1 | grep -v '"RequestId"' || true
  done
  echo "Policies attached."
else
  echo "Root account detected, skipping policy attachment."
fi
