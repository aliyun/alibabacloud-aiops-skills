#!/bin/bash
# ==============================================================================
# PAI-EAS Service Deployment Script
# Create PAI-EAS service using JSON configuration
#
# Usage:
#   ./create-service-from-json.sh --config service.json
#   ./create-service-from-json.sh --config-json '{"metadata":{"name":"xxx"...}}'
#   ./create-service-from-json.sh --config service.json --region cn-hangzhou
#
# Output:
#   JSON format, containing service creation result
# ==============================================================================

set -euo pipefail

# Parameter parsing
CONFIG_FILE=""
CONFIG_JSON=""
REGION=""
WAIT_READY=true
TIMEOUT=300

while [[ $# -gt 0 ]]; do
  case $1 in
    --config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    --config-json)
      CONFIG_JSON="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --no-wait)
      WAIT_READY=false
      shift
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Usage:
  $0 --config service.json
  $0 --config-json '{"metadata":{"name":"xxx"...}}'
  $0 --config service.json --region cn-hangzhou

Parameters:
  --config FILE       JSON config file path
  --config-json JSON  JSON config string
  --region REGION     Region, defaults to ALIBABACLOUD_REGION env var
  --no-wait           Do not wait for service to be ready
  --timeout SECONDS   Wait timeout in seconds, default 300
  -h, --help          Show help information

Environment Variables:
  ALIBABACLOUD_REGION     Region (if --region not specified)

Examples:
  # Deploy from file
  $0 --config service.json --region cn-hangzhou

  # Deploy from JSON string
  $0 --config-json '{"metadata":{"name":"test"},"containers":[{"image":"..."}]}'

  # Do not wait for ready
  $0 --config service.json --no-wait

Output format:
  Success: {"success":true,"service_id":"...","service_name":"...","status":"Running"}
  Failure: {"success":false,"error":"...","service_name":"..."}
EOF
      exit 0
      ;;
    *)
      echo "Unknown parameter: $1" >&2
      exit 1
      ;;
  esac
done

# Check environment variables
if [[ -z "$REGION" ]]; then
  REGION="${ALIBABACLOUD_REGION:-}"
fi

if [[ -z "$REGION" ]]; then
  echo '{"success":false,"error":"Please specify --region or set ALIBABACLOUD_REGION environment variable"}'
  exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read config
if [[ -n "$CONFIG_FILE" ]]; then
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "{\"success\":false,\"error\":\"Config file does not exist: $CONFIG_FILE\"}"
    exit 1
  fi
  CONFIG=$(cat "$CONFIG_FILE")
elif [[ -n "$CONFIG_JSON" ]]; then
  CONFIG="$CONFIG_JSON"
else
  echo '{"success":false,"error":"Please provide --config or --config-json parameter"}'
  exit 1
fi

# Validate config
echo "Validating config..." >&2
VALIDATION=$("$SCRIPT_DIR/validate-service-config.sh" --config-json "$CONFIG" --fix 2>/dev/null)

if [[ $? -ne 0 ]]; then
  ERROR=$(echo "$VALIDATION" | jq -r '.errors | join("; ")')
  echo "{\"success\":false,\"error\":\"Config validation failed: $ERROR\"}"
  exit 1
fi

# Extract fixed config
FIXED_CONFIG=$(echo "$VALIDATION" | jq -c '.fixed_config')

# Extract service name
SERVICE_NAME=$(echo "$FIXED_CONFIG" | jq -r '.metadata.name')

echo "Service name: $SERVICE_NAME" >&2
echo "Config validation passed" >&2

# Create service
echo "Creating service..." >&2
CREATE_RESULT=$(aliyun eas create-service \
  --cluster-id "$REGION" \
  --body "$FIXED_CONFIG" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy \
  2>&1)

# Check creation result
if echo "$CREATE_RESULT" | jq -e '.ServiceId' > /dev/null 2>&1; then
  SERVICE_ID=$(echo "$CREATE_RESULT" | jq -r '.ServiceId')
  echo "Service created successfully: $SERVICE_ID" >&2
  
  # Wait for service ready
  if [[ "$WAIT_READY" == "true" ]]; then
    echo "Waiting for service to be ready..." >&2
    
    START_TIME=$(date +%s)
    while true; do
      CURRENT_TIME=$(date +%s)
      ELAPSED=$((CURRENT_TIME - START_TIME))
      
      if [[ $ELAPSED -gt $TIMEOUT ]]; then
        echo "{\"success\":false,\"error\":\"Timeout waiting for service to be ready\",\"service_id\":\"$SERVICE_ID\",\"service_name\":\"$SERVICE_NAME\"}"
        exit 1
      fi
      
      # Query service status
      SERVICE_INFO=$(aliyun eas describe-service \
        --cluster-id "$REGION" \
        --service-name "$SERVICE_NAME" \
        --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy \
        2>&1)
      
      if ! echo "$SERVICE_INFO" | jq -e '.Status' > /dev/null 2>&1; then
        echo "Failed to query service status, retrying..." >&2
        sleep 5
        continue
      fi
      
      STATUS=$(echo "$SERVICE_INFO" | jq -r '.Status')
      MESSAGE=$(echo "$SERVICE_INFO" | jq -r '.Message // empty')
      
      case $STATUS in
        "Running")
          echo "Service is ready" >&2
          ENDPOINT=$(echo "$SERVICE_INFO" | jq -r '.InternetEndpoint // empty')
          INTRANET_ENDPOINT=$(echo "$SERVICE_INFO" | jq -r '.IntranetEndpoint // empty')
          echo "{\"success\":true,\"service_id\":\"$SERVICE_ID\",\"service_name\":\"$SERVICE_NAME\",\"status\":\"Running\",\"internet_endpoint\":\"$ENDPOINT\",\"intranet_endpoint\":\"$INTRANET_ENDPOINT\"}"
          exit 0
          ;;
        "Failed")
          echo "Service startup failed: $MESSAGE" >&2
          echo "{\"success\":false,\"error\":\"Service startup failed: $MESSAGE\",\"service_id\":\"$SERVICE_ID\",\"service_name\":\"$SERVICE_NAME\"}"
          exit 1
          ;;
        *)
          echo "Waiting for service to be ready... ($ELAPSED/$TIMEOUT sec) Status: $STATUS" >&2
          sleep 5
          ;;
      esac
    done
  else
    # Do not wait, return immediately
    echo "{\"success\":true,\"service_id\":\"$SERVICE_ID\",\"service_name\":\"$SERVICE_NAME\",\"status\":\"Creating\"}"
    exit 0
  fi
else
  # Creation failed
  ERROR_MSG=$(echo "$CREATE_RESULT" | jq -r '.Message // .')
  echo "Service creation failed: $ERROR_MSG" >&2
  echo "{\"success\":false,\"error\":\"Service creation failed: $ERROR_MSG\",\"service_name\":\"$SERVICE_NAME\"}"
  exit 1
fi
