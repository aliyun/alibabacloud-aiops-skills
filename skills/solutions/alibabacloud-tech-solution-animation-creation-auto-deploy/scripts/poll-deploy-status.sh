#!/bin/bash
set -euo pipefail

# Step 5: Poll deployment status until complete (typically 5-15 minutes)
# Required env var: PROJECT_NAME

ENV_NAME="production"
POLL_INTERVAL=30
MAX_POLLS=40

if [ -z "${PROJECT_NAME:-}" ]; then
  echo "ERROR: Environment variable PROJECT_NAME is not set" >&2
  exit 1
fi

echo "Waiting for deployment to finish..."
for i in $(seq 1 $MAX_POLLS); do
  RESULT=$(aliyun devs get-environment --project-name "$PROJECT_NAME" --name "$ENV_NAME" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1)
  COMFYUI_PHASE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',{}).get('servicesInstances',{}).get('comfyui',{}).get('latestDeployment',{}).get('phase','N/A'))" 2>/dev/null)
  WEB_PHASE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',{}).get('servicesInstances',{}).get('web',{}).get('latestDeployment',{}).get('phase','N/A'))" 2>/dev/null)
  echo "[$(date +%H:%M:%S)] Poll #$i: comfyui=$COMFYUI_PHASE, web=$WEB_PHASE"
  if [ "$COMFYUI_PHASE" = "Finished" ] && [ "$WEB_PHASE" = "Finished" ]; then
    echo "Deploy SUCCESS"
    exit 0
  fi
  if [ "$COMFYUI_PHASE" = "Failed" ] || [ "$WEB_PHASE" = "Failed" ]; then
    echo "Deploy FAILED — check error details above"
    exit 1
  fi
  sleep $POLL_INTERVAL
done

echo "Deploy TIMEOUT — exceeded $MAX_POLLS polling attempts"
exit 1
