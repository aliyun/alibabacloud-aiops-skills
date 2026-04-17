#!/bin/bash
set -euo pipefail

# Step 1: Auto-create Bailian API Key
# Check workspace → Create if missing → Create API Key → Export API_KEY variable
# Use `source` to ensure API_KEY is exported to the current shell

DESCRIPTION="AI Animation Story Creation App"

# Get workspace list
WORKSPACE_RESULT=$(aliyun modelstudio list-workspaces --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null)
WORKSPACE_COUNT=$(echo "$WORKSPACE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('totalCount', 0))")

# If no workspace exists, create one automatically
if [ "$WORKSPACE_COUNT" = "0" ]; then
  echo "No Bailian workspace found, creating one..."
  CREATE_WS_RESULT=$(aliyun modelstudio create-workspace \
    --workspace-name "default" \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1)
  WORKSPACE_ID=$(echo "$CREATE_WS_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['workspace']['workspaceId'])")
  echo "Workspace created: $WORKSPACE_ID"
else
  WORKSPACE_ID=$(echo "$WORKSPACE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['workspaces'][0]['workspaceId'])")
  echo "Workspace: $WORKSPACE_ID"
fi

# Create API Key
CREATE_RESULT=$(aliyun modelstudio create-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --description "$DESCRIPTION" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1)

# Extract API Key value and ID
API_KEY=$(echo "$CREATE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['apiKey']['apiKeyValue'])")
API_KEY_ID=$(echo "$CREATE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['apiKey']['apiKeyId'])")
export API_KEY
export API_KEY_ID
echo "API_KEY=$API_KEY"
echo "API_KEY_ID=$API_KEY_ID"
