#!/bin/bash
set -euo pipefail

# Step 4a: Render template → filter custom-domain → add roleArn → UpdateEnvironment
# Required env vars: PROJECT_NAME, BUCKET_NAME, API_KEY
# Optional env var: MY_UID (auto-fetched if not set)

REGION="cn-hangzhou"
TEMPLATE_NAME="animation-creation"
ROLE_NAME="aliyundevscustomrole"
ENV_NAME="production"

for var in PROJECT_NAME BUCKET_NAME API_KEY; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: Environment variable $var is not set" >&2
    exit 1
  fi
done

# Auto-fetch MY_UID
if [ -z "${MY_UID:-}" ]; then
  MY_UID=$(aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['AccountId'])")
  export MY_UID
fi

ROLE_ARN="acs:ram::${MY_UID}:role/${ROLE_NAME}"

# Render template
RENDER_OUTPUT=$(aliyun devs render-services-by-template \
  --template-name "$TEMPLATE_NAME" \
  --project-name "$PROJECT_NAME" \
  --variable-values "{\"shared\":{\"namespace\":\"$PROJECT_NAME\",\"region\":\"$REGION\",\"ossBucket\":\"$BUCKET_NAME\",\"bailian_api_key\":\"$API_KEY\",\"fc_role_arn\":\"$ROLE_ARN\"}}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1)

# Filter custom-domain from render result and build UpdateEnvironment body
UPDATE_BODY=$(echo "$RENDER_OUTPUT" | python3 -c "
import sys,json
data = json.load(sys.stdin)
services = {k:v for k,v in data['services'].items() if k != 'custom-domain'}
body = {'name':'$ENV_NAME','spec':{'roleArn':'$ROLE_ARN','stagedConfigs':{'services':services}}}
print(json.dumps(body, ensure_ascii=False))
")

# Update environment config (must use --body, not --spec)
aliyun devs update-environment \
  --project-name "$PROJECT_NAME" \
  --name "$ENV_NAME" \
  --body "$UPDATE_BODY" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
