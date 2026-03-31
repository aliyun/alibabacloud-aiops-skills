#!/usr/bin/env bash

readonly ALIYUN_USER_AGENT="AlibabaCloud-Agent-Skills"
readonly -a ALIYUN_CMD=(aliyun --user-agent "$ALIYUN_USER_AGENT")

require_arg() {
    local flag="$1"
    local value="$2"
    local example="${3:-}"

    if [[ -n "$value" ]]; then
        return 0
    fi

    echo "Error: $flag is required." >&2
    if [[ -n "$example" ]]; then
        echo "       Example: $example" >&2
    fi
    exit 1
}

require_prefix() {
    local flag="$1"
    local value="$2"
    local prefix="$3"

    if [[ "$value" =~ ^${prefix} ]]; then
        return 0
    fi

    echo "Error: $flag must start with '${prefix}'." >&2
    echo "       Received: \"$value\"" >&2
    exit 1
}

run_cli() {
    local error_message="$1"
    shift

    local output
    output=$("$@" 2>&1) || {
        echo "Error: $error_message" >&2
        echo "$output" >&2
        return 1
    }

    printf '%s' "$output"
}

run_api_dry_run() {
    local output
    output=$("$@" 2>&1)
    local status=$?

    if [[ $status -eq 0 ]]; then
        printf '%s' "$output"
        return 0
    fi

    if [[ "$output" == *"DryRunOperation"* ]]; then
        printf '%s' "$output"
        return 0
    fi

    printf '%s' "$output"
    return 1
}

normalize_json_output() {
    python3 -c '
import json
import sys

raw = sys.stdin.read()
text = raw.strip()

if not text:
    sys.exit(1)

def emit(obj):
    print(json.dumps(obj))
    raise SystemExit(0)

try:
    emit(json.loads(text))
except Exception:
    pass

decoder = json.JSONDecoder()
for idx, ch in enumerate(raw):
    if ch not in "{[":
        continue
    try:
        obj, _end = decoder.raw_decode(raw, idx)
        emit(obj)
    except Exception:
        continue

sys.exit(1)
'
}

wait_for_json_field() {
    local resource_name="$1"
    local field_path="$2"
    local expected_value="$3"
    local max_attempts="$4"
    local sleep_seconds="$5"
    local error_message="$6"
    shift 6

    local attempt=""
    local output=""
    local current_value=""

    for ((attempt = 1; attempt <= max_attempts; attempt++)); do
        output=$(run_cli "$error_message" "$@") || return 1
        current_value=$(printf '%s' "$output" | json_get_field "$field_path" "")
        if [[ "$current_value" == "$expected_value" ]]; then
            printf '%s' "$output"
            return 0
        fi
        if (( attempt < max_attempts )); then
            sleep "$sleep_seconds"
        fi
    done

    echo "Error: $resource_name did not reach expected state '$expected_value'." >&2
    printf '%s\n' "$output" >&2
    return 1
}

json_get_field() {
    local field_path="$1"
    local default_value="${2:-}"

    normalize_json_output | python3 -c '
import json
import sys

field_path = sys.argv[1]
default_value = sys.argv[2]

value = json.load(sys.stdin)

for part in field_path.split("."):
    if isinstance(value, dict):
        if part not in value:
            value = default_value
            break
        value = value[part]
    elif isinstance(value, list):
        try:
            index = int(part)
        except ValueError:
            value = default_value
            break
        if index < 0 or index >= len(value):
            value = default_value
            break
        value = value[index]
    else:
        value = default_value
        break

if value is None:
    value = default_value

if isinstance(value, (dict, list)):
    print(json.dumps(value))
else:
    print(value)
' "$field_path" "$default_value"
}

paginate_collection() {
    local item_key="$1"
    local error_message="$2"
    shift 2

    local items_file
    items_file=$(mktemp)
    printf '[]' > "$items_file"

    local next_token=""
    local page=""
    local result=""

    while true; do
        if [[ -n "$next_token" ]]; then
            page=$(run_cli "$error_message" "$@" --next-token "$next_token") || {
                rm -f "$items_file"
                return 1
            }
        else
            page=$(run_cli "$error_message" "$@") || {
                rm -f "$items_file"
                return 1
            }
        fi

        printf '%s' "$page" | normalize_json_output | python3 -c '
import json
import sys

item_key = sys.argv[1]
items_path = sys.argv[2]

page = json.load(sys.stdin)
with open(items_path, "r", encoding="utf-8") as fh:
    items = json.load(fh)

items.extend(page.get(item_key, []))

with open(items_path, "w", encoding="utf-8") as fh:
    json.dump(items, fh)
' "$item_key" "$items_file" || {
            echo "Error: Failed to parse paginated response for $item_key." >&2
            rm -f "$items_file"
            return 1
        }

        next_token=$(printf '%s' "$page" | json_get_field "NextToken" "") || {
            echo "Error: Failed to parse NextToken for $item_key." >&2
            rm -f "$items_file"
            return 1
        }
        if [[ -z "$next_token" ]]; then
            break
        fi
    done

    result=$(python3 - "$item_key" "$items_file" <<'PY'
import json
import sys

item_key = sys.argv[1]
items_path = sys.argv[2]

with open(items_path, "r", encoding="utf-8") as fh:
    items = json.load(fh)

print(json.dumps({item_key: items}))
PY
    ) || {
        echo "Error: Failed to build aggregated response for $item_key." >&2
        rm -f "$items_file"
        return 1
    }

    rm -f "$items_file"
    printf '%s' "$result"
}

write_output() {
    local output_file="$1"
    local formatter="$2"

    if [[ -n "$output_file" ]]; then
        "$formatter" > "$output_file"
        echo "Output written to $output_file"
    else
        "$formatter"
    fi
}
