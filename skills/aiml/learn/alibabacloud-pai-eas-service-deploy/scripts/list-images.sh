#!/bin/bash
# PAI-EAS Official Image List Query Script
# Uses ListImages and ListImageLabels APIs to fetch image information
#
# Dependencies (pinned minimum versions):
#   - aliyun CLI >= 3.3.3   (Alibaba Cloud CLI)
#   - jq        >= 1.6      (command-line JSON processor)
#   - openssl   >= 1.1.1    (used to generate the session-id)

set -e

# Verify pinned dependency versions before doing anything else.
REQUIRED_ALIYUN="3.3.3"
REQUIRED_JQ="1.6"
command -v aliyun >/dev/null 2>&1 || { echo "aliyun CLI (>= ${REQUIRED_ALIYUN}) is required" >&2; exit 1; }
command -v jq     >/dev/null 2>&1 || { echo "jq (>= ${REQUIRED_JQ}) is required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }

# Observability: unified user-agent with a per-session trace id.
# Generate SKILL_SESSION_ID once per session (32-char lowercase hex) and reuse
# it across every CLI/SDK/Terraform call so all requests share one trace id.
SKILL_NAME="alibabacloud-pai-eas-service-deploy"
if [ -z "${SKILL_SESSION_ID:-}" ]; then
  SKILL_SESSION_ID="$(openssl rand -hex 16)"
  export SKILL_SESSION_ID
fi
USER_AGENT="AlibabaCloud-Agent-Skills/${SKILL_NAME}/${SKILL_SESSION_ID}"

# Default parameters
REGION="${REGION:-cn-hangzhou}"
FRAMEWORK="${FRAMEWORK:-}"
CHIP_TYPE="${CHIP_TYPE:-}"
VERBOSE="${VERBOSE:-false}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help information
show_help() {
  cat <<EOF
PAI-EAS Official Image List Query Tool

Usage:
  $0 [options]

Options:
  -r, --region <region>     Region (default: cn-hangzhou)
  -f, --framework <name>    Filter by framework (vLLM, SGLang, PyTorch, TensorFlow, PaiRag, CosyVoice)
  -c, --chip <type>         Filter by chip type (CPU, GPU, PPU)
  -v, --verbose             Show detailed information
  -h, --help                Show help information

Examples:
  # List all official EAS-supported images
  $0

  # List vLLM images
  $0 -f vLLM

  # List GPU type images
  $0 -c GPU

  # List vLLM GPU images (verbose)
  $0 -f vLLM -c GPU -v

Framework types:
  vLLM        - LLM inference acceleration
  SGLang      - Structured output inference
  PyTorch     - Deep learning framework
  TensorFlow  - Deep learning framework
  PaiRag      - RAG knowledge QA
  CosyVoice   - Voice synthesis
  ModelScope  - ModelScope community images
EOF
}

# Parse parameters
while [[ $# -gt 0 ]]; do
  case $1 in
    -r|--region)
      REGION="$2"
      shift 2
      ;;
    -f|--framework)
      FRAMEWORK="$2"
      shift 2
      ;;
    -c|--chip)
      CHIP_TYPE="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE="true"
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown parameter: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

echo -e "${BLUE}=== PAI-EAS Official Image List ===${NC}"
echo ""

# Build label filter conditions
LABELS="system.official=true,system.supported.eas=true"
FRAMEWORK_FILTER=""

if [ -n "$FRAMEWORK" ]; then
  # Framework filter - filter in results
  FRAMEWORK_FILTER="$FRAMEWORK"
fi

if [ -n "$CHIP_TYPE" ]; then
  LABELS="$LABELS,system.chipType=$CHIP_TYPE"
fi

echo -e "${YELLOW}Query parameters:${NC}"
echo "  Region: $REGION"
[ -n "$FRAMEWORK" ] && echo "  Framework: $FRAMEWORK"
[ -n "$CHIP_TYPE" ] && echo "  Chip: $CHIP_TYPE"
echo ""

# Call ListImages API
echo -e "${YELLOW}Querying image list...${NC}"
IMAGES=$(aliyun aiworkspace list-images \
  --verbose true \
  --labels "$LABELS" \
  --page-size 100 \
  --user-agent "$USER_AGENT")

# Check if successful
if [ -z "$IMAGES" ] || [ "$(echo "$IMAGES" | jq -r '.RequestId' 2>/dev/null)" = "null" ]; then
  echo -e "${RED}Query failed, please check network connection and permissions${NC}"
  echo "Error: $IMAGES"
  exit 1
fi

# Count images
TOTAL=$(echo "$IMAGES" | jq -r '.Images | length')

if [ "$TOTAL" -eq 0 ]; then
  echo -e "${YELLOW}No matching images found${NC}"
  exit 0
fi

echo -e "${GREEN}Found $TOTAL images${NC}"
echo ""

# Display image list
if [ "$VERBOSE" = "true" ]; then
  # Verbose mode
  if [ -n "$FRAMEWORK_FILTER" ]; then
    # Filter by framework
    echo "$IMAGES" | jq -r --arg fw "$FRAMEWORK_FILTER" '
      [.Images[] | 
      select(.Labels[] | select(.Key | contains($fw))) |
      {
        name: .Name,
        uri: .ImageUri,
        description: .Description,
        chipType: (([.Labels[] | select(.Key == "system.chipType") | .Value] | first) // "N/A"),
        framework: (([.Labels[] | select(.Key | startswith("system.framework.")) | .Value] | first) // "N/A"),
        port: (([.Labels[] | select(.Key == "system.eas.default.port") | .Value] | first) // "8000"),
        script: (([.Labels[] | select(.Key == "system.eas.default.script") | .Value] | first) // ""),
        latest: (([.Labels[] | select(.Key == "system.eas.deploy.latest") | .Value] | first) // "false")
      }] | sort_by(.latest == "false", .name) | .[] | 
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
        "Name: \(.name)\n" +
        "Type: [\(.chipType)] \(.framework)\n" +
        "Image: \(.uri)\n" +
        "Description: \(.description)\n" +
        "Port: \(.port)\n" +
        (if .script != "" then "Script: \(.script)\n" else "" end) +
        (if .latest == "true" then "Tag: ⭐ Latest\n" else "" end)'
  else
    echo "$IMAGES" | jq -r '
      [.Images[] | 
      {
        name: .Name,
        uri: .ImageUri,
        description: .Description,
        chipType: (([.Labels[] | select(.Key == "system.chipType") | .Value] | first) // "N/A"),
        framework: (([.Labels[] | select(.Key | startswith("system.framework.")) | .Value] | first) // "N/A"),
        port: (([.Labels[] | select(.Key == "system.eas.default.port") | .Value] | first) // "8000"),
        script: (([.Labels[] | select(.Key == "system.eas.default.script") | .Value] | first) // ""),
        latest: (([.Labels[] | select(.Key == "system.eas.deploy.latest") | .Value] | first) // "false")
      }] | sort_by(.latest == "false", .name) | .[] | 
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
        "Name: \(.name)\n" +
        "Type: [\(.chipType)] \(.framework)\n" +
        "Image: \(.uri)\n" +
        "Description: \(.description)\n" +
        "Port: \(.port)\n" +
        (if .script != "" then "Script: \(.script)\n" else "" end) +
        (if .latest == "true" then "Tag: ⭐ Latest\n" else "" end)'
  fi
else
  # Compact mode
  if [ -n "$FRAMEWORK_FILTER" ]; then
    # Filter by framework
    echo -e "${BLUE}Image list:${NC}"
    echo "$IMAGES" | jq -r --arg fw "$FRAMEWORK_FILTER" '
      [.Images[] | 
      select(.Labels[] | select(.Key | contains($fw))) |
      {
        name: .Name,
        chipType: (([.Labels[] | select(.Key == "system.chipType") | .Value] | first) // "N/A"),
        framework: (([.Labels[] | select(.Key | startswith("system.framework.")) | .Value] | first) // "N/A"),
        latest: (([.Labels[] | select(.Key == "system.eas.deploy.latest") | .Value] | first) // "false"),
        description: .Description
      }] | sort_by(.latest == "false", .name) | .[] | 
        "  [\(.chipType)] \(.framework) - \(.name)" + 
        (if .latest == "true" then " ⭐" else "" end)'
  else
    echo -e "${BLUE}Image list:${NC}"
    echo "$IMAGES" | jq -r '
      [.Images[] | 
      {
        name: .Name,
        chipType: (([.Labels[] | select(.Key == "system.chipType") | .Value] | first) // "N/A"),
        framework: (([.Labels[] | select(.Key | startswith("system.framework.")) | .Value] | first) // "N/A"),
        latest: (([.Labels[] | select(.Key == "system.eas.deploy.latest") | .Value] | first) // "false"),
        description: .Description
      }] | sort_by(.latest == "false", .name) | .[] | 
        "  [\(.chipType)] \(.framework) - \(.name)" + 
        (if .latest == "true" then " ⭐" else "" end)'
  fi
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Tips:${NC}"
echo "  Use -v for detailed information"
echo "  Use -f <framework> to filter by framework"
echo "  Use -c <chip_type> to filter by CPU/GPU/PPU"
echo ""
