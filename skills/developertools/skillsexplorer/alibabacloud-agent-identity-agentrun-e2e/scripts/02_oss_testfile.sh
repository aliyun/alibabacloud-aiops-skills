#!/usr/bin/env bash
# 02_oss_testfile.sh — create the OSS test bucket + hello.txt used by the
# sample's read_oss_file tool (Group C). oss2 authenticates through the aliyun
# CLI credential chain (oss_provider_snippet); no AccessKey is read here.
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

init_conda || fail "run 00_detect_env.sh first"
load_e2e_env
ACCOUNT_ID="${ACCOUNT_ID:?ACCOUNT_ID missing — run 00_detect_env.sh}"
E2E_OSS_BUCKET="${E2E_OSS_BUCKET:-e2e-test-${ACCOUNT_ID}}"
E2E_OSS_KEY="${E2E_OSS_KEY:-hello.txt}"
save_kv E2E_OSS_BUCKET "$E2E_OSS_BUCKET"
save_kv E2E_OSS_KEY "$E2E_OSS_KEY"

ensure_oss_deps

# The provider preamble is prepended OUTSIDE the quoted heredoc, so the Python
# body below stays literal (no shell expansion of $ or backticks).
export SKILL_UA
SKILL_UA=$(ua_string)
{
  oss_provider_snippet
  cat <<'PYEOF'

bucket_name = os.environ["E2E_OSS_BUCKET"]
key = os.environ["E2E_OSS_KEY"]
region = os.environ["E2E_OSS_REGION"]

bucket = oss2.Bucket(oss_auth(), f"https://oss-{region}.aliyuncs.com", bucket_name,
                     region=region, app_name=OSS_UA)
try:
    bucket.create_bucket(oss2.BUCKET_ACL_PRIVATE)
    print("[OK] bucket created:", bucket_name)
except oss2.exceptions.BucketAlreadyExists:
    print("[SKIP] bucket exists:", bucket_name)
bucket.put_object(key, "AgentRun e2e test file: OSS STS read verification.")
print("[OK] uploaded:", key)
print("[OK] read-back:", bucket.get_object(key).read().decode()[:60])
PYEOF
} | E2E_OSS_BUCKET="$E2E_OSS_BUCKET" E2E_OSS_KEY="$E2E_OSS_KEY" \
    E2E_OSS_REGION="$E2E_OSS_REGION" python3 - || fail "OSS prepare failed"

log_ok "OSS test file ready: ${E2E_OSS_BUCKET}/${E2E_OSS_KEY} (${E2E_OSS_REGION})"
