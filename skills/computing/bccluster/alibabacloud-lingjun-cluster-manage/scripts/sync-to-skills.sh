#!/usr/bin/env bash
# Dependencies: bash 3.2+, rsync, coreutils (dev-only utility; not required at skill runtime)
# 把 workspace 当前内容兜底同步到 Qoder / QoderWork 的 skill 安装目录
# 用法:
#   bash scripts/sync-to-skills.sh                  # 默认 dry-run, 只列 diff
#   bash scripts/sync-to-skills.sh --apply          # 真实同步 (增量, 不删多余)
#   bash scripts/sync-to-skills.sh --apply --mirror # 镜像 (删除目标多余文件)
#   bash scripts/sync-to-skills.sh --target <DIR>   # 指定额外目标 (可重复)
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"

# 默认目标: Qoder + QoderWork 标准安装路径
TARGETS=(
  "$HOME/.qoder/skills/alibabacloud-lingjun-cluster-manage"
  "$HOME/.qoderwork/skills/alibabacloud-lingjun-cluster-manage"
)

# 忽略路径 (与 .gitignore 主要项对齐)
EXCLUDES=(
  --exclude=.git
  --exclude=.qoder
  --exclude=.qwen
  --exclude=.claude
  --exclude=.agents
  --exclude=.tmp-tests
  --exclude=.DS_Store
  --exclude=node_modules
  --exclude=__pycache__
  --exclude='*.pyc'
  --exclude='*.bak'
  --exclude='*.swp'
  --exclude='validation-result-*.json'
  --exclude=tests/reports
  --exclude=skills-lock.json
)

MODE="dry"
MIRROR=0
EXTRA_TARGETS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)    MODE="apply"; shift ;;
    --dry-run)  MODE="dry"; shift ;;
    --mirror)   MIRROR=1; shift ;;
    --target)   EXTRA_TARGETS+=("$2"); shift 2 ;;
    -h|--help)  sed -n '2,9p' "$0"; exit 0 ;;
    *)          echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

[[ ${#EXTRA_TARGETS[@]} -gt 0 ]] && TARGETS=("${EXTRA_TARGETS[@]}")

RSYNC_OPTS=(-a --human-readable --itemize-changes)
[[ "$MODE" == "dry" ]] && RSYNC_OPTS+=(--dry-run)
[[ "$MIRROR" == "1" ]] && RSYNC_OPTS+=(--delete)

printf '源: %s\n模式: %s  镜像: %s\n\n' "$SRC" "$MODE" "$MIRROR"

any_diff=0
for dest in "${TARGETS[@]}"; do
  if [[ ! -d "$dest" ]]; then
    printf '⚠ 跳过 (目录不存在): %s\n\n' "$dest"
    continue
  fi
  printf '===== → %s =====\n' "$dest"
  out=$(rsync "${RSYNC_OPTS[@]}" "${EXCLUDES[@]}" "$SRC/" "$dest/" 2>&1 || true)
  if [[ -n "$out" ]]; then
    printf '%s\n' "$out"
    any_diff=1
  else
    echo "  (无差异)"
  fi
  echo
done

if [[ "$MODE" == "dry" ]]; then
  if [[ "$any_diff" == "1" ]]; then
    echo "ℹ 演练显示存在差异，如需真实同步: bash $0 --apply"
  else
    echo "✅ 演练完成: 所有目标已与源一致, 无需同步"
  fi
  exit 0
fi

echo "✅ 同步完成"
exit 0
