#!/usr/bin/env bash
# 03_build.sh — build the deployment zip for the sample (cross-platform
# dependency vendoring). The pipeline below is field-verified; do NOT
# simplify it (see references/packaging.md for why each part exists):
#   1. a FULLY-PINNED constraints file (partial pinning caused
#      dependency drift — mcp 2.0.0 crashed the runtime with
#      "operation not permitted"; the full lock below is the 2026-08-16
#      known-good set that passed the whole verification matrix)
#   2. multi manylinux platform tags (single manylinux2014 misses modern wheels)
#   3. local wheels for sdist-only transitive deps (crcmod needs a Linux
#      binary — auto-repacked from prior build artifacts when found;
#      utils/oss2/tea-family build locally as pure-python wheels)
#   4. a post-install version self-check of the critical packages
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

init_conda || fail "run 00_detect_env.sh first"
load_e2e_env
PROJECT_DIR=$(require_project_dir)

cd "$PROJECT_DIR"

# --- constraints: FULL known-good lock (field-verified) ------
CONS="$STATE_DIR/constraints.txt"
mkdir -p "$STATE_DIR"
cat > "$CONS" <<'EOF'
ag_ui_protocol==0.1.19
aiofiles==24.1.0
aiohappyeyeballs==2.6.2
aiohttp==3.14.1
aiosignal==1.4.0
alibabacloud_bailian20231229==2.13.0
alibabacloud_credentials==1.0.9
alibabacloud_credentials_api==1.0.0
alibabacloud_devs20230714==2.4.1
alibabacloud_endpoint_util==0.0.4
alibabacloud_gateway_spi==0.0.3
alibabacloud_gpdb20160503==5.3.0
alibabacloud_openapi_util==0.2.4
alibabacloud_tea==0.4.3
alibabacloud_tea_openapi==0.4.4
alibabacloud_tea_util==0.3.14
aliyun_python_sdk_core==2.16.0
aliyun_python_sdk_kms==2.16.5
annotated_doc==0.0.4
annotated_types==0.7.0
anyio==4.13.0
apscheduler==3.11.2
attrs==26.1.0
certifi==2026.5.20
cffi==2.0.0
charset_normalizer==3.4.7
click==8.4.1
crc32c==2.8
crcmod==1.7
cryptography==46.0.7
darabonba_core==1.0.6
distro==1.9.0
fastapi==0.136.3
flatbuffers==25.12.19
frozenlist==1.8.0
future==1.0.0
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
httpx_sse==0.4.3
idna==3.18
jiter==0.15.0
jmespath==0.10.0
jsonpatch==1.33
jsonpointer==3.1.1
jsonschema==4.26.0
jsonschema_specifications==2025.9.1
langchain==1.3.8
langchain_core==1.4.6
langchain_openai==1.3.0
langchain_protocol==0.0.16
langgraph==1.2.4
langgraph_checkpoint==4.1.1
langgraph_prebuilt==1.1.0
langgraph_sdk==0.4.2
langsmith==0.8.15
mcp==1.27.2
multidict==6.7.1
numpy==2.4.6
openai==2.41.1
orjson==3.11.9
ormsgpack==1.12.2
oss2==2.19.1
packaging==26.2
propcache==0.5.2
protobuf==5.29.6
pycparser==3.0
pycryptodome==3.23.0
pydantic==2.13.4
pydantic_core==2.46.4
pydantic_settings==2.14.1
pydash==8.0.6
pyjwt==2.13.0
python_dotenv==1.2.2
python_multipart==0.0.32
pyyaml==6.0.3
referencing==0.37.0
regex==2026.5.9
requests==2.34.2
requests_toolbelt==1.0.0
rpds_py==2026.5.1
six==1.17.0
sniffio==1.3.1
sse_starlette==3.4.4
starlette==1.3.0
tablestore==6.4.6
tablestore_agent_storage==1.0.6
tenacity==9.1.4
tiktoken==0.13.0
tqdm==4.68.2
typing_extensions==4.15.0
typing_inspection==0.4.2
tzlocal==5.3.1
urllib3==2.7.0
uuid_utils==0.16.0
uvicorn==0.49.0
websockets==15.0.1
xxhash==3.7.0
yarl==1.24.2
zstandard==0.25.0
agentrun-sdk==0.0.52
agent-identity-python-sdk==0.1.5
agent-identity-cli==0.1.1
alibabacloud-oss-v2==1.3.2
EOF

# --- local wheels for sdist-only deps ------------------------------------------
WHEELS="$STATE_DIR/wheels"
mkdir -p "$WHEELS"
log_info "building local wheels for sdist-only pure-python deps (utils, oss2, tea family)..."
python3 -m pip wheel --no-deps -q -w "$WHEELS" \
  "utils>=1.0.2" "oss2==2.19.1" \
  "alibabacloud-tea==0.4.3" "alibabacloud-tea-util==0.3.14" \
  "alibabacloud-openapi-util==0.2.4" "alibabacloud-endpoint-util==0.0.4" \
  "alibabacloud-credentials==1.0.9" "alibabacloud-credentials-api==1.0.0" \
  "alibabacloud-gateway-spi==0.0.3" "darabonba-core==1.0.6" \
  "aliyun-python-sdk-core==2.16.0" \
  || fail "local wheel build failed"

# crcmod: needs a manylinux BINARY wheel; PyPI ships sdist only.
# try PyPI first, then AUTO-REPACK the compiled crcmod from any prior
# linux build artifacts before giving up. Candidate sources (first hit wins):
#   $E2E_CRCMOD_SRC (explicit), the sample dir's own prior build residue,
#   any sibling kit sample dir with vendored deps.
if ! ls "$WHEELS"/crcmod-*.whl >/dev/null 2>&1; then
  python3 -m pip download --no-deps -q -d "$WHEELS" \
    --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
    --platform manylinux_2_28_x86_64 --python-version 3.12 \
    --only-binary=:all: "crcmod==1.7" 2>/dev/null || true
fi
if ! ls "$WHEELS"/crcmod-*.whl >/dev/null 2>&1; then
  for cand in "${E2E_CRCMOD_SRC:-}" \
              "$PROJECT_DIR/crcmod" \
              "$PROJECT_DIR"/../agentrun-e2e_sample/crcmod \
              "$PROJECT_DIR"/../*/crcmod; do
    [ -d "$cand" ] && [ -d "$(dirname "$cand")/crcmod-1.7.dist-info" ] || continue
    base=$(dirname "$cand")
    /usr/bin/zip -qr "$WHEELS/crcmod-1.7-cp312-cp312-manylinux2014_x86_64.whl" \
      -j "$base/crcmod" "$base/crcmod-1.7.dist-info" 2>/dev/null || continue
    # re-zip preserving the top-level layout (dist-info must sit at zip root)
    rm -f "$WHEELS/crcmod-1.7-cp312-cp312-manylinux2014_x86_64.whl"
    ( cd "$base" && /usr/bin/zip -qr "$WHEELS/crcmod-1.7-cp312-cp312-manylinux2014_x86_64.whl" \
        crcmod crcmod-1.7.dist-info ) \
      && log_ok "crcmod wheel repacked from: $base" && break
  done
fi
if ! ls "$WHEELS"/crcmod-*.whl >/dev/null 2>&1; then
  log_fail "crcmod manylinux wheel unavailable."
  echo "  PyPI ships sdist only. Provide a prior linux build's compiled crcmod" >&2
  echo "  via E2E_CRCMOD_SRC=<dir containing crcmod/ and crcmod-1.7.dist-info/>" >&2
  echo "  See references/packaging.md section 4 (crcmod)." >&2
  exit 1
fi

# --- main install ----------------------------------------------------------------
log_info "vendoring dependencies into the sample dir (this takes a few minutes)..."
python3 -m pip install -r requirements.txt -t . \
  --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
  --platform manylinux_2_28_x86_64 \
  --python-version 3.12 --only-binary=:all: \
  --find-links "$WHEELS" -c "$CONS" \
  || fail "pip vendoring failed — compare the error with references/packaging.md"

# --- version self-check: critical packages must match the lock ----------
log_info "critical package versions:"
check_pkg() {
  local dir expected ver name
  # dist-info dirs use wheel naming (underscores) while the lock file uses
  # release names (hyphens) — normalize before grepping the constraints
  name="${1//_/-}"
  dir=$(ls -d "$1"-*.dist-info 2>/dev/null | head -1) || true
  [ -n "$dir" ] || { log_fail "MISSING package dir: $1"; exit 1; }
  ver=$(echo "$dir" | sed -E "s/^$1-([0-9][^-]*)\.dist-info/\1/")
  expected=$(grep -iE "^$name==" "$CONS" | head -1 | cut -d= -f3)
  if [ "$ver" = "$expected" ]; then
    log_ok "$1==$ver"
  else
    log_fail "$1==$ver BUT lock says $expected (dependency drift)"
    exit 1
  fi
}
check_pkg mcp
check_pkg langchain
check_pkg fastapi
check_pkg openai
check_pkg agentrun_sdk
check_pkg agent_identity_python_sdk

# --- zip ---------------------------------------------------------------------------
ZIP="${E2E_ZIP:-$STATE_DIR/agentrun-e2e-sample.zip}"
rm -f "$ZIP"
/usr/bin/zip -qr "$ZIP" . -x "*__pycache__*"
save_kv E2E_ZIP "$ZIP"
log_ok "built: $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "NEXT: upload this zip in the AgentRun console (references/agentrun-deploy.md)"
