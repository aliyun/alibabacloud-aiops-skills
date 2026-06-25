#!/bin/bash

# Hook script that detects write operations.
# Used to prevent any mutating operation during the inspection workflow.

# Capture the command being executed
COMMAND="$1"

# List of keywords that indicate a write operation
WRITE_KEYWORDS=(
    "INSERT"
    "UPDATE"
    "DELETE"
    "CREATE"
    "DROP"
    "ALTER"
    "TRUNCATE"
    "REPLACE"
    "GRANT"
    "REVOKE"
    "SET.*="
    "BEGIN"
    "COMMIT"
    "ROLLBACK"
)

# Check whether the command contains any write-operation keyword
for keyword in "${WRITE_KEYWORDS[@]}"; do
    if echo "$COMMAND" | grep -i -E "$keyword" > /dev/null 2>&1; then
        echo "[BLOCKED] Potential write operation detected: $keyword"
        echo "This skill is read-only and forbids any mutating operation."
        echo "If a mutating operation is required, please confirm and run it manually."
        exit 1
    fi
done

# No write operation detected; allow execution
exit 0
