#!/bin/bash
# ==============================================================================
# PAI-EAS Service Config Validator
# Validate service JSON config, apply defaults, output validation result
#
# Usage:
#   ./validate-service-config.sh --config service.json
#   ./validate-service-config.sh --config service.json --fix
#   ./validate-service-config.sh --config-json '{"metadata":{"name":"xxx"...}}'
#   ./validate-service-config.sh --config service.json --output service-fixed.json
#
# Output:
#   JSON format, containing validation result and fixed config
# ==============================================================================

set -euo pipefail

# Parameter parsing
CONFIG_FILE=""
CONFIG_JSON=""
FIX_MODE=false
OUTPUT_FILE=""

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
    --fix)
      FIX_MODE=true
      shift
      ;;
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Usage:
  $0 --config service.json
  $0 --config service.json --fix
  $0 --config-json '{"metadata":{"name":"xxx"...}}'

Parameters:
  --config FILE       JSON config file path
  --config-json JSON  JSON config string
  --fix               Output the fixed complete config
  --output FILE       Output fixed config to file
  -h, --help          Show help information

Validation rules:
  1. Required field check: metadata.name, containers[].image
  2. Service name format: ^[a-z0-9_]+$
  3. Image URI format check
  4. Resource config completeness check
  5. Storage mount check (warning for official images)
  6. Apply defaults (port, instance count, etc.)

Output format:
  {
    "valid": true/false,
    "errors": [...],
    "warnings": [...],
    "fixed_config": {...}  // output in --fix mode
  }
EOF
      exit 0
      ;;
    *)
      echo "Unknown parameter: $1" >&2
      exit 1
      ;;
  esac
done

# Read config
if [[ -n "$CONFIG_FILE" ]]; then
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo '{"valid":false,"errors":["Config file does not exist: '"$CONFIG_FILE"'"],"warnings":[]}' 
    exit 1
  fi
  CONFIG=$(cat "$CONFIG_FILE")
elif [[ -n "$CONFIG_JSON" ]]; then
  CONFIG="$CONFIG_JSON"
else
  echo '{"valid":false,"errors":["Please provide --config or --config-json parameter"],"warnings":[]}' 
  exit 1
fi

# Check JSON format
if ! echo "$CONFIG" | jq empty 2>/dev/null; then
  echo '{"valid":false,"errors":["Invalid JSON format"],"warnings":[]}'
  exit 1
fi

# Extract fields
NAME=$(echo "$CONFIG" | jq -r '.metadata.name // empty')
INSTANCE=$(echo "$CONFIG" | jq -r '.metadata.instance // empty')
WORKSPACE_ID=$(echo "$CONFIG" | jq -r '.metadata.workspace_id // empty')
RESOURCE=$(echo "$CONFIG" | jq -r '.metadata.resource // empty')
CONTAINERS=$(echo "$CONFIG" | jq -c '.containers // []')
CLOUD_COMPUTING=$(echo "$CONFIG" | jq -c '.cloud.computing // empty')
CLOUD_NETWORKING=$(echo "$CONFIG" | jq -c '.cloud.networking // empty')
STORAGE=$(echo "$CONFIG" | jq -c '.storage // []')
NETWORKING=$(echo "$CONFIG" | jq -c '.networking // empty')

# Initialize errors and warnings
ERRORS="[]"
WARNINGS="[]"

# 1. Required field check
if [[ -z "$NAME" ]]; then
  ERRORS=$(echo "$ERRORS" | jq '. + ["metadata.name is a required field"]')
fi

CONTAINER_COUNT=$(echo "$CONTAINERS" | jq 'length')
if [[ "$CONTAINER_COUNT" -eq 0 ]]; then
  ERRORS=$(echo "$ERRORS" | jq '. + ["containers is a required field, at least one container config is needed"]')
else
  # Check image field for each container
  for i in $(seq 0 $((CONTAINER_COUNT - 1))); do
    IMAGE=$(echo "$CONTAINERS" | jq -r ".[$i].image // empty")
    if [[ -z "$IMAGE" ]]; then
      ERRORS=$(echo "$ERRORS" | jq ". + [\"containers[$i].image is a required field\"]")
    else
      # Simple image format check
      if [[ ! "$IMAGE" =~ ^[a-zA-Z0-9._/-]+(:[a-zA-Z0-9._-]+)?$ ]]; then
        WARNINGS=$(echo "$WARNINGS" | jq ". + [\"containers[$i].image format may be incorrect: $IMAGE\"]")
      fi
    fi
  done
fi

# 2. Service name format check
if [[ -n "$NAME" ]] && [[ ! "$NAME" =~ ^[a-z0-9_]+$ ]]; then
  ERRORS=$(echo "$ERRORS" | jq ". + [\"metadata.name format error, only lowercase letters, numbers, and underscores allowed: $NAME\"]")
fi

# 3. Resource config check
HAS_RESOURCE=false
HAS_CLOUD_COMPUTING=false

if [[ -n "$RESOURCE" ]]; then
  HAS_RESOURCE=true
fi

if [[ -n "$CLOUD_COMPUTING" ]] && [[ "$CLOUD_COMPUTING" != "null" ]]; then
  HAS_CLOUD_COMPUTING=true
  INSTANCE_TYPE=$(echo "$CLOUD_COMPUTING" | jq -r '.instance_type // empty')
  INSTANCES=$(echo "$CLOUD_COMPUTING" | jq -c '.instances // []')
  
  if [[ -z "$INSTANCE_TYPE" ]] && [[ $(echo "$INSTANCES" | jq 'length') -eq 0 ]]; then
    ERRORS=$(echo "$ERRORS" | jq '. + ["cloud.computing requires instance_type or instances configuration"]')
  fi
fi

if [[ "$HAS_RESOURCE" == "false" ]] && [[ "$HAS_CLOUD_COMPUTING" == "false" ]]; then
  ERRORS=$(echo "$ERRORS" | jq '. + ["Either metadata.resource (dedicated resource group) or cloud.computing (public resource group) must be configured"]')
fi

# 4. Network config check (for dedicated gateway)
GATEWAY=$(echo "$NETWORKING" | jq -r '.gateway // empty')
if [[ -n "$GATEWAY" ]]; then
  # Check if "shared" is incorrectly set as gateway
  if [[ "$GATEWAY" == "shared" ]]; then
    ERRORS=$(echo "$ERRORS" | jq '. + ["Shared gateway does not need networking.gateway field, please remove it"]')
  else
    # Dedicated gateway requires VPC config
    VPC_ID=$(echo "$CLOUD_NETWORKING" | jq -r '.vpc_id // empty')
    VSWITCH_ID=$(echo "$CLOUD_NETWORKING" | jq -r '.vswitch_id // empty')
    SECURITY_GROUP_ID=$(echo "$CLOUD_NETWORKING" | jq -r '.security_group_id // empty')

    if [[ -z "$VPC_ID" ]] || [[ -z "$VSWITCH_ID" ]] || [[ -z "$SECURITY_GROUP_ID" ]]; then
      ERRORS=$(echo "$ERRORS" | jq '. + ["When using dedicated gateway, cloud.networking must include vpc_id, vswitch_id, security_group_id"]')
    fi
  fi
fi

# 5. Storage mount check
STORAGE_COUNT=$(echo "$STORAGE" | jq 'length')
if [[ "$STORAGE_COUNT" -eq 0 ]]; then
  WARNINGS=$(echo "$WARNINGS" | jq '. + ["No storage mount configured, official images require model files to be mounted"]')
else
  # Check OSS path format
  for i in $(seq 0 $((STORAGE_COUNT - 1))); do
    OSS_PATH=$(echo "$STORAGE" | jq -r ".[$i].oss.path // empty")
    if [[ -n "$OSS_PATH" ]]; then
      if [[ ! "$OSS_PATH" =~ ^oss:// ]]; then
        ERRORS=$(echo "$ERRORS" | jq ". + [\"storage[$i].oss.path format error, must start with oss://: $OSS_PATH\"]")
      fi
    fi
  done
fi

# 6. Check unsupported config types
PROCESSOR=$(echo "$CONFIG" | jq -r '.processor // empty')
MODEL=$(echo "$CONFIG" | jq -r '.model // empty')

if [[ -n "$PROCESSOR" ]]; then
  ERRORS=$(echo "$ERRORS" | jq '. + ["processor deployment is not supported, please use containers image deployment"]')
fi

if [[ -n "$MODEL" ]]; then
  ERRORS=$(echo "$ERRORS" | jq '. + ["model deployment is not supported, please use containers image deployment"]')
fi

# 7. Check quota config (not supported)
QUOTA_ID=$(echo "$CONFIG" | jq -r '.metadata.quota_id // empty')
if [[ -n "$QUOTA_ID" ]]; then
  WARNINGS=$(echo "$WARNINGS" | jq '. + ["Quota resource group is not supported, quota_id config will be ignored"]')
fi

# Build result
ERROR_COUNT=$(echo "$ERRORS" | jq 'length')
if [[ "$ERROR_COUNT" -gt 0 ]]; then
  VALID="false"
else
  VALID="true"
fi

# Apply defaults function
apply_defaults() {
  local config="$1"

  # Apply defaults
  echo "$config" | jq '
    # Default instance count
    if .metadata.instance == null or .metadata.instance == "" then
      .metadata.instance = 1
    else . end

    # Default container port
    | .containers = (.containers | map(
        if .port == null or .port == "" then
          .port = 8000
        else . end
      ))

    # Default shared memory size
    | if .metadata.shm_size == null or .metadata.shm_size == "" then
      .metadata.shm_size = 64
    else . end

    # Default graceful termination period
    | if .runtime.termination_grace_period == null or .runtime.termination_grace_period == "" then
      .runtime.termination_grace_period = 30
    else . end

    # Default keepalive timeout
    | if .rpc.keepalive == null or .rpc.keepalive == "" then
      .rpc.keepalive = 600
    else . end

    # Shared gateway: remove networking field (not needed for shared gateway)
    | if .networking.gateway == "shared" or .networking.gateway == "" or .networking.gateway == null then
      del(.networking)
    else . end
  '
}

# Main logic
if [[ "$FIX_MODE" == "true" ]] && [[ "$VALID" == "true" ]]; then
  FIXED_CONFIG=$(apply_defaults "$CONFIG")
  if [[ -n "$OUTPUT_FILE" ]]; then
    echo "$FIXED_CONFIG" | jq '.' > "$OUTPUT_FILE"
    echo "{\"valid\":$VALID,\"errors\":$ERRORS,\"warnings\":$WARNINGS,\"output_file\":\"$OUTPUT_FILE\"}"
  else
    echo "{\"valid\":$VALID,\"errors\":$ERRORS,\"warnings\":$WARNINGS,\"fixed_config\":$FIXED_CONFIG}"
  fi
elif [[ -n "$OUTPUT_FILE" ]]; then
  # Output config to file (even with errors, output for user to fix)
  echo "$CONFIG" | jq '.' > "$OUTPUT_FILE"
  echo "{\"valid\":$VALID,\"errors\":$ERRORS,\"warnings\":$WARNINGS,\"output_file\":\"$OUTPUT_FILE\"}"
else
  echo "{\"valid\":$VALID,\"errors\":$ERRORS,\"warnings\":$WARNINGS}"
fi

if [[ "$VALID" == "false" ]]; then
  exit 1
fi

exit 0
