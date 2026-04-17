#!/bin/bash
# upload_to_oss.sh - Upload text file to OSS (auto-fetch credentials)
# Usage: ./upload_to_oss.sh <local_file>
# Returns: FileURL (for subsequent job submission)

set -e

# Constants
MAX_FILE_SIZE=5242880  # 5MB in bytes
CLI_TIMEOUT=60        # CLI command timeout in seconds
UPLOAD_TIMEOUT=120    # OSS upload timeout in seconds
ALLOWED_EXTENSIONS="txt docx"

# Run command with timeout (cross-platform: timeout > gtimeout > no timeout)
# Usage: run_with_timeout <timeout_seconds> <command...>
run_with_timeout() {
    local timeout_sec="$1"
    shift
    
    if command -v timeout &> /dev/null; then
        timeout "${timeout_sec}s" "$@"
    elif command -v gtimeout &> /dev/null; then
        gtimeout "${timeout_sec}s" "$@"
    else
        "$@"
    fi
}

# JSON value extraction function (no external dependencies required)
# Tries: jq > python3 > grep/sed fallback
json_get() {
    local json="$1"
    local key="$2"
    
    # Try jq first (fastest)
    if command -v jq &> /dev/null; then
        echo "$json" | jq -r ".$key // empty"
        return
    fi
    
    # Try python3
    if command -v python3 &> /dev/null; then
        echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$key',''))"
        return
    fi
    
    # Fallback: grep/sed (works on all systems)
    echo "$json" | grep -o "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed "s/\"$key\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\"/\1/" | head -1
}

if [ $# -lt 1 ]; then
    echo "Usage: $0 <local_file>"
    exit 1
fi

LOCAL_FILE="$1"

# Security: Validate file path (prevent path traversal)
if [[ "$LOCAL_FILE" == *".."* ]]; then
    echo "Error: Invalid file path (path traversal not allowed)"
    exit 1
fi

# Resolve to absolute path and verify it's under allowed directories
REAL_PATH=$(realpath "$LOCAL_FILE" 2>/dev/null || echo "")
if [ -z "$REAL_PATH" ]; then
    echo "Error: Cannot resolve file path: $LOCAL_FILE"
    exit 1
fi

# Check if file exists
if [ ! -f "$REAL_PATH" ]; then
    echo "Error: File not found: $LOCAL_FILE"
    exit 1
fi

# Get file extension and validate
FILE_EXT="${LOCAL_FILE##*.}"
FILE_EXT_LOWER=$(echo "$FILE_EXT" | tr '[:upper:]' '[:lower:]')

if [[ ! " $ALLOWED_EXTENSIONS " =~ " $FILE_EXT_LOWER " ]]; then
    echo "Error: Invalid file type '$FILE_EXT'. Allowed types: $ALLOWED_EXTENSIONS"
    exit 1
fi

# Validate file size (max 5MB)
FILE_SIZE=$(stat -f%z "$REAL_PATH" 2>/dev/null || stat -c%s "$REAL_PATH" 2>/dev/null || echo "0")
if [ "$FILE_SIZE" -gt "$MAX_FILE_SIZE" ]; then
    echo "Error: File size (${FILE_SIZE} bytes) exceeds maximum allowed (${MAX_FILE_SIZE} bytes / 5MB)"
    exit 1
fi

echo "[1/2] Getting upload credentials..."

# Get upload credentials (with timeout)
UPLOAD_RESP=$(run_with_timeout $CLI_TIMEOUT aliyun ice create-yike-asset-upload \
  --file-ext "$FILE_EXT" \
  --file-type StoryboardInput \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard 2>&1) || {
    if [ $? -eq 124 ]; then
        echo "Error: CLI command timed out after ${CLI_TIMEOUT}s"
        exit 1
    fi
}

FILE_URL=$(json_get "$UPLOAD_RESP" "FileURL")
UPLOAD_AUTH=$(json_get "$UPLOAD_RESP" "UploadAuth")
UPLOAD_ADDRESS=$(json_get "$UPLOAD_RESP" "UploadAddress")

if [ -z "$FILE_URL" ]; then
    echo "Error: Failed to get upload credentials"
    echo "$UPLOAD_RESP"
    exit 1
fi

# Decode Base64
AUTH_JSON=$(echo "$UPLOAD_AUTH" | base64 -d)
ADDR_JSON=$(echo "$UPLOAD_ADDRESS" | base64 -d)

# Extract STS credentials
ACCESS_KEY_ID=$(json_get "$AUTH_JSON" "AccessKeyId")
ACCESS_KEY_SECRET=$(json_get "$AUTH_JSON" "AccessKeySecret")
SECURITY_TOKEN=$(json_get "$AUTH_JSON" "SecurityToken")
REGION=$(json_get "$AUTH_JSON" "Region")

# Extract OSS info
ENDPOINT=$(json_get "$ADDR_JSON" "Endpoint")
BUCKET=$(json_get "$ADDR_JSON" "Bucket")
FILE_NAME=$(json_get "$ADDR_JSON" "FileName")

echo "[2/2] Uploading file to OSS..."
echo "  Bucket: $BUCKET"
echo "  Object: $FILE_NAME"

# Execute upload (with timeout)
run_with_timeout $UPLOAD_TIMEOUT aliyun ossutil cp "$REAL_PATH" "oss://${BUCKET}/${FILE_NAME}" \
  --mode StsToken \
  --access-key-id "$ACCESS_KEY_ID" \
  --access-key-secret "$ACCESS_KEY_SECRET" \
  --sts-token "$SECURITY_TOKEN" \
  --endpoint "$ENDPOINT" 2>&1 || {
    if [ $? -eq 124 ]; then
        echo "Error: OSS upload timed out after ${UPLOAD_TIMEOUT}s"
        exit 1
    fi
    exit 1
}

echo ""
echo "Upload successful!"
echo "FileURL: $FILE_URL"
