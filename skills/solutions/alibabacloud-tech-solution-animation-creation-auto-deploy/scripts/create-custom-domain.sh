#!/bin/bash
set -euo pipefail

# Step 6: Create custom domain
# Get token → Create helper function → Register DNS → Create FC custom domain → Clean up helper function
# Required env var: PROJECT_NAME
# Optional env var: MY_UID (auto-fetched if not set)

REGION="cn-hangzhou"
HELPER_SERVICE="serverless-devs-check"

if [ -z "${PROJECT_NAME:-}" ]; then
  echo "ERROR: Environment variable PROJECT_NAME is not set" >&2
  exit 1
fi

# Auto-fetch MY_UID
if [ -z "${MY_UID:-}" ]; then
  MY_UID=$(aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['AccountId'])")
  export MY_UID
fi

DOMAIN_NAME="${PROJECT_NAME}-web.fcv3.${MY_UID}.${REGION}.fc.devsapp.net"
FC_FUNCTION="${PROJECT_NAME}-web"

# 6a. Get domain verification token
TOKEN=$(curl -s --connect-timeout 10 --max-time 30 -A AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy -X POST "https://domain.devsapp.net/token" \
  --data-urlencode "type=fc" \
  --data-urlencode "user=$MY_UID" \
  --data-urlencode "region=$REGION" \
  --data-urlencode "service=fcv3" \
  --data-urlencode "function=$FC_FUNCTION" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['Response']['Body']['Token'])")
echo "Token: $TOKEN"

# 6b. Create helper service (ignore AlreadyExists error)
aliyun fc-open create-service --body "{\"serviceName\":\"$HELPER_SERVICE\",\"description\":\"domain check\"}" --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null || true

# 6b. Create helper function
aliyun fc-open create-function --service-name "$HELPER_SERVICE" \
  --body "{\"functionName\":\"domain${TOKEN}\",\"handler\":\"index.handler\",\"runtime\":\"nodejs14\",\"code\":{\"zipFile\":\"UEsDBAoAAAAIABULiFLOAhlFSQAAAE0AAAAIAAAAaW5kZXguanMdyMEJwCAMBdBVclNBskCxuxT9UGiJNgnFg8MX+o4Pc3R14/OQdkOpUFQ8mRQ2MtUujumJyv4PG6TFob3CjCEve78gtBaFkLYPUEsBAh4DCgAAAAgAFQuIUs4CGUVJAAAATQAAAAgAAAAAAAAAAAAAALSBAAAAAGluZGV4LmpzUEsFBgAAAAABAAEANgAAAG8AAAAAAA==\"},\"environmentVariables\":{\"token\":\"${TOKEN}\"},\"memorySize\":128,\"timeout\":3}" \
  --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# 6b. Create helper HTTP trigger
aliyun fc-open create-trigger --service-name "$HELPER_SERVICE" \
  --function-name "domain${TOKEN}" \
  --body '{"triggerName":"httpTrigger","triggerType":"http","triggerConfig":"{\"AuthType\":\"anonymous\",\"Methods\":[\"POST\",\"GET\"]}"}' \
  --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# 6c. Register devsapp.net DNS CNAME
DNS_RESULT=$(curl -s --connect-timeout 10 --max-time 30 -A AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy -X POST "https://domain.devsapp.net/domain" \
  --data-urlencode "type=fc" \
  --data-urlencode "user=$MY_UID" \
  --data-urlencode "region=$REGION" \
  --data-urlencode "service=fcv3" \
  --data-urlencode "function=$FC_FUNCTION" \
  --data-urlencode "token=$TOKEN")
echo "DNS registration result: $DNS_RESULT"
# Check if DNS registration succeeded
echo "$DNS_RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('Response', {}).get('Success') == False:
        print('ERROR: DNS registration failed', file=sys.stderr)
        sys.exit(1)
except (json.JSONDecodeError, KeyError):
    pass
"

# 6c. Create FC custom domain
aliyun fc create-custom-domain --body "{\"domainName\":\"${DOMAIN_NAME}\",\"protocol\":\"HTTP\",\"routeConfig\":{\"routes\":[{\"functionName\":\"$FC_FUNCTION\",\"methods\":[\"GET\",\"POST\",\"PUT\",\"DELETE\",\"OPTIONS\"],\"path\":\"/*\",\"qualifier\":\"LATEST\"}]}}" --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# 6d. Clean up helper function and service
aliyun fc-open delete-trigger --service-name "$HELPER_SERVICE" --function-name "domain${TOKEN}" --trigger-name httpTrigger --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null || true
aliyun fc-open delete-function --service-name "$HELPER_SERVICE" --function-name "domain${TOKEN}" --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null || true
aliyun fc-open delete-service --service-name "$HELPER_SERVICE" --region "$REGION" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>/dev/null || true

echo "Custom domain created: http://${DOMAIN_NAME}/"
