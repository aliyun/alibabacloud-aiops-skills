#!/bin/bash
set -euo pipefail

# Step 4b: Trigger deployment (built-in rate-limit protection, max 3 retries, 60s interval)
# Required env var: PROJECT_NAME

ENV_NAME="production"
MAX_RETRIES=3
RETRY_INTERVAL=60

if [ -z "${PROJECT_NAME:-}" ]; then
  echo "ERROR: Environment variable PROJECT_NAME is not set" >&2
  exit 1
fi

for i in $(seq 1 $MAX_RETRIES); do
  echo "[$(date +%H:%M:%S)] DeployEnvironment attempt ${i}/${MAX_RETRIES}..."
  RESULT=$(aliyun devs deploy-environment \
    --project-name "$PROJECT_NAME" \
    --name "$ENV_NAME" \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1) && RC=0 || RC=$?

  # Check success (return code 0 and output contains valid JSON / no error)
  if [ $RC -eq 0 ]; then
    HTTP_CODE=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('HttpCode', data.get('httpCode', 200)))
except:
    print(200)
" 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "202" ]; then
      echo "DeployEnvironment SUCCESS"
      echo "$RESULT"
      exit 0
    fi
  fi

  # Parse error code
  ERROR_CODE=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('Code', data.get('code', 'Unknown')))
except:
    print('Unknown')
" 2>/dev/null)

  echo "[$(date +%H:%M:%S)] Failed — error: $ERROR_CODE"
  echo "$RESULT"

  # 404 means environment does not exist, no need to retry
  if echo "$RESULT" | grep -q '"HttpCode":404\|"httpCode":404\|NotFound'; then
    echo "ERROR: Environment not found (404), check whether Step 3 create-project completed successfully" >&2
    exit 1
  fi

  # No need to wait after the last attempt
  if [ $i -lt $MAX_RETRIES ]; then
    echo "[$(date +%H:%M:%S)] Waiting ${RETRY_INTERVAL}s before retrying..."
    sleep $RETRY_INTERVAL
  fi
done

echo "ERROR: DeployEnvironment failed ${MAX_RETRIES} consecutive times, stopping retries" >&2
exit 1
