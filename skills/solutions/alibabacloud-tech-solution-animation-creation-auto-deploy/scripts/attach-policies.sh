#!/bin/bash
set -euo pipefail

# RAM Policy: Auto-detect identity type and attach required policies
# No env vars needed — identity info is fetched automatically

POLICIES="AliyunOSSFullAccess AliyunFCFullAccess"

IDENTITY=$(aliyun sts GetCallerIdentity --user-agent AlibabaCloud-Agent-Skills 2>&1)
IDENTITY_TYPE=$(echo "$IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['IdentityType'])")

if [ "$IDENTITY_TYPE" = "RAMUser" ]; then
  RAM_USER=$(echo "$IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'].split('/')[-1])")
  echo "RAM user: $RAM_USER, auto-attaching required policies..."
  for POLICY in $POLICIES; do
    aliyun ram AttachPolicyToUser --PolicyType System --PolicyName "$POLICY" --UserName "$RAM_USER" --user-agent AlibabaCloud-Agent-Skills 2>&1 | grep -v '"RequestId"' || true
  done
  echo "Policies attached."
else
  echo "Root account detected, skipping policy attachment."
fi
