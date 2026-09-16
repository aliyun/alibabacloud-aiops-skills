#!/bin/zsh
# Sign a private OSS object with ossutil V4 (works with long-term AK and STS).
# Usage: zsh oss_sign_clean.sh oss://bucket/key [ttl-seconds] [region-or-endpoint]
set -e
OBJ="${1:?oss://bucket/object required}"
TTL="${2:-86400}"
REGION="${3:-cn-beijing}"
REGION="${REGION#oss-}"
REGION="${REGION%.aliyuncs.com}"

URL=$(aliyun ossutil presign "$OBJ" \
  --expires-duration "${TTL}s" \
  --region "$REGION" \
  --sign-version v4 \
  --output-format raw)

echo "URL: $URL"
code=$(curl -s -o /dev/null -w '%{http_code}' -r 0-2048 "$URL")
echo "verify: HTTP $code"
if [ "$code" = "206" ] || [ "$code" = "200" ]; then
  if command -v pbcopy >/dev/null; then
    printf '%s' "$URL" | pbcopy
    echo "verified and copied to clipboard (Cmd+V to paste)"
  else
    echo "verified"
  fi
else
  echo "verification failed (HTTP $code); NOT copied"
  exit 1
fi
