#!/usr/bin/env bash
# detect_python.sh — Detect available Python >= 3.7 and output its path
# Usage: PYTHON=$(bash scripts/detect_python.sh) || exit 1

for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
  if command -v "$cmd" &>/dev/null; then
    ver=$("$cmd" -c "import sys; print(sys.version_info >= (3,7))" 2>/dev/null)
    if [ "$ver" = "True" ]; then
      echo "$cmd"
      exit 0
    fi
  fi
done

echo "Error: Python >= 3.7 not found" >&2
exit 1
