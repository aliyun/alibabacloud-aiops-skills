# Acceptance Criteria: sls-index-config-manager

**Scenario**: SLS Index Configuration Management
**Purpose**: Skill testing acceptance criteria

Cloud API examples below assume `SLS_INDEX_USER_AGENT` was initialized once using
[Observability](../SKILL.md#observability).

---

## Correct CLI Invocation Patterns

### 1. Command Format — verify product and API name

#### CORRECT

```bash
aliyun sls get-index --user-agent "$SLS_INDEX_USER_AGENT" --project my-project --logstore my-logstore

aliyun sls create-index --user-agent "$SLS_INDEX_USER_AGENT" \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)"


aliyun sls delete-index --user-agent "$SLS_INDEX_USER_AGENT" --project my-project --logstore my-logstore
```

#### INCORRECT — Wrong product name

```bash
aliyun log get-index --project my-project --logstore my-logstore
aliyun logservice create-index --project p --logstore l
```

**Why**: Product name is `sls`, not `log`, `logservice`, `aliyunlog`, or `aliyun-sls`.

### 2. Parameter Format

#### CORRECT — Kebab-case sub-command and flags

```bash
aliyun sls update-index --user-agent "$SLS_INDEX_USER_AGENT" \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)" \
  --max-text-len 4096
```

#### INCORRECT — PascalCase sub-command or flags

```bash
aliyun sls UpdateIndex --Project p --Logstore l --Keys ...
aliyun sls GetIndex --Project p
```

**Why**: The SLS plugin uses **kebab-case** for both sub-commands (`get-index`, `create-index`, `update-index`, `delete-index`) and flags (`--project`, `--logstore`, `--line`, `--keys`, `--max-text-len`).

#### INCORRECT — JSON `--params` blob

```bash
aliyun sls update-index --user-agent "$SLS_INDEX_USER_AGENT" --params '{"Project":"p","Logstore":"l","Keys":{...}}'
```

**Why**: The CLI takes individual flags, not a JSON `--params` blob.

### 3. Index Body Passing — prefer files

Prefer JSON files for complex `line` and `keys` values to simplify quoting. Correctly quoted
inline JSON or serialized variables are also acceptable.

```bash
aliyun sls create-index --user-agent "$SLS_INDEX_USER_AGENT" \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)"
```

### 4. UpdateIndex — complete config replacement

#### CORRECT — Submit the complete final config

```bash
aliyun sls get-index --user-agent "$SLS_INDEX_USER_AGENT" --project my-project --logstore my-logstore > /tmp/current.json

# Prepare /tmp/line.json and /tmp/keys.json as the final complete config.

aliyun sls update-index --user-agent "$SLS_INDEX_USER_AGENT" \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)" \
  --max-text-len 2048
```

#### INCORRECT — Sending only a partial field fragment

```bash
aliyun sls update-index --user-agent "$SLS_INDEX_USER_AGENT" \
  --project my-project --logstore my-logstore \
  --keys '{"new_field":{"type":"long","doc_value":true}}'
```

**Why**: `update-index` is overwrite — submitting only `keys` drops `line`, `max_text_len`, `log_reduce`, and every existing field that was not re-included.

### 5. CreateIndex vs UpdateIndex — pick by current state

#### CORRECT — Branch on whether `get-index` succeeds

```bash
if aliyun sls get-index --user-agent "$SLS_INDEX_USER_AGENT" --project p --logstore l > /tmp/cur.json 2>/tmp/err; then
  aliyun sls update-index --user-agent "$SLS_INDEX_USER_AGENT" \
    --project p --logstore l \
    --line "$(cat /tmp/line.json)" \
    --keys "$(cat /tmp/keys.json)"
else
  grep -q IndexConfigNotExist /tmp/err && \
    aliyun sls create-index --user-agent "$SLS_INDEX_USER_AGENT" \
      --project p --logstore l \
      --line "$(cat /tmp/line.json)" \
      --keys "$(cat /tmp/keys.json)"
fi
```

#### INCORRECT — Always calling create-index

```bash
aliyun sls create-index --user-agent "$SLS_INDEX_USER_AGENT" --project p --logstore l --line "..." --keys "..."
```

**Why**: If an index already exists, `create-index` fails with `IndexAlreadyExist`. Always inspect first.

### 6. DeleteIndex — dangerous operation

Deleting an index removes full-text and field indexes and restricts indexed search and SQL
analytics. Explain the impact, obtain explicit authorization for the target, and save a backup.
Do not request confirmation again when the user has already explicitly authorized deletion.

#### CORRECT — Confirm and capture a snapshot before deleting

```bash
aliyun sls get-index --user-agent "$SLS_INDEX_USER_AGENT" --project p --logstore l > /tmp/index-backup-$(date +%s).json

# After explicit user confirmation:
aliyun sls delete-index --user-agent "$SLS_INDEX_USER_AGENT" --project p --logstore l
```

### 7. Authentication — never expose credentials

#### CORRECT — Verify credential profile via default credential chain

```bash
aliyun configure list
```

#### INCORRECT — Passing AK/SK directly in the command

```bash
aliyun sls update-index --user-agent "$SLS_INDEX_USER_AGENT" \
  --access-key-id LTAI5tXXXX \
  --access-key-secret 8dXXXX \
  --project p --logstore l --line "..."
```

**Why**: Credentials must come from the configured profile, environment variables, STS, or RAM role — never be typed into the command line.

#### INCORRECT — Reading or printing raw credentials

```bash
aliyun configure get        # FORBIDDEN: may expose credential details
cat ~/.aliyun/config.json   # FORBIDDEN: may expose credential details
```

#### INCORRECT — Any command that prints environment credentials

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID       # FORBIDDEN
printenv | grep -i credential           # FORBIDDEN
env | grep -i access_key                # FORBIDDEN
```

### 8. Region Parameter

Use the global `--region` flag with a full region ID, for example `--region cn-hangzhou`.

### 9. Versioned User-Agent

Use the manifest-derived version and a fresh random 32-character
lowercase hexadecimal session ID. Reuse this skill's UA for all calls and retries in the
conversation. Every cloud API command and request-only dry run must pass it as one quoted
`--user-agent` value. Missing/invalid manifest data must fail before any cloud call; do not
guess a version. Local help, version, plugin and configure commands are exempt.

## Workflow Checklist

When the skill executes a write, it must satisfy all of:

- [ ] `update-index` body is the **full** desired configuration, not a partial fragment.
- [ ] For `delete-index`, the user gave explicit confirmation and a backup file was written.
