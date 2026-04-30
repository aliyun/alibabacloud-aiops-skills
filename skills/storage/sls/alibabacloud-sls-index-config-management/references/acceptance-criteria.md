# Acceptance Criteria: sls-index-config-manager

**Scenario**: SLS Index Configuration Management
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Invocation Patterns

### 1. Command Format — verify product and API name

#### CORRECT

```bash
aliyun sls get-index --project my-project --logstore my-logstore

aliyun sls create-index \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)"


aliyun sls delete-index --project my-project --logstore my-logstore
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
aliyun sls update-index \
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
aliyun sls update-index --params '{"Project":"p","Logstore":"l","Keys":{...}}'
```

**Why**: The CLI takes individual flags, not a JSON `--params` blob.

### 3. Index Body Passing — always via file

#### CORRECT — Write JSON to file, then pass with `$(cat ...)`

```bash
cat > /tmp/line.json <<'EOF'
{
  "caseSensitive": false,
  "chn": false,
  "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
}
EOF

cat > /tmp/keys.json <<'EOF'
{
  "status": { "type": "long", "doc_value": true },
  "request_uri": {
    "type": "text",
    "doc_value": true,
    "caseSensitive": false,
    "chn": false,
    "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", ":", "/", "\n", "\t", "\r"]
  }
}
EOF

aliyun sls create-index \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)"
```

#### INCORRECT — Inline multi-line JSON with shell-special characters

```bash
aliyun sls create-index --project p --logstore l \
  --keys '{
    "request_uri": {"type":"text","token":[",", " ", "\n", "\t"]}
  }'
```

**Why**: Tokenizer arrays usually contain backslash escapes (`\n`, `\t`, `\r`) and quotes. Inline multi-line JSON in the shell breaks quoting; always serialize to a file first.

### 4. UpdateIndex — complete config replacement

#### CORRECT — Submit the complete final config

```bash
aliyun sls get-index --project my-project --logstore my-logstore > /tmp/current.json

# Prepare /tmp/line.json and /tmp/keys.json as the final complete config.

aliyun sls update-index \
  --project my-project --logstore my-logstore \
  --line "$(cat /tmp/line.json)" \
  --keys "$(cat /tmp/keys.json)" \
  --max-text-len 2048
```

#### INCORRECT — Sending only a partial field fragment

```bash
aliyun sls update-index \
  --project my-project --logstore my-logstore \
  --keys '{"new_field":{"type":"long","doc_value":true}}'
```

**Why**: `update-index` is overwrite — submitting only `keys` drops `line`, `max_text_len`, `log_reduce`, and every existing field that was not re-included.

### 5. CreateIndex vs UpdateIndex — pick by current state

#### CORRECT — Branch on whether `get-index` succeeds

```bash
if aliyun sls get-index --project p --logstore l > /tmp/cur.json 2>/tmp/err; then
  aliyun sls update-index \
    --project p --logstore l \
    --line "$(cat /tmp/line.json)" \
    --keys "$(cat /tmp/keys.json)"
else
  grep -q IndexConfigNotExist /tmp/err && \
    aliyun sls create-index \
      --project p --logstore l \
      --line "$(cat /tmp/line.json)" \
      --keys "$(cat /tmp/keys.json)"
fi
```

#### INCORRECT — Always calling create-index

```bash
aliyun sls create-index --project p --logstore l --line "..." --keys "..."
```

**Why**: If an index already exists, `create-index` fails with `IndexAlreadyExist`. Always inspect first.

### 6. DeleteIndex — explicit confirmation required

#### CORRECT — Confirm and capture a snapshot before deleting

```bash
aliyun sls get-index --project p --logstore l > /tmp/index-backup-$(date +%s).json

# After explicit user confirmation:
aliyun sls delete-index --project p --logstore l
```

#### INCORRECT — Chaining delete-index after a write

```bash
aliyun sls update-index --project p --logstore l --line "..."
aliyun sls delete-index --project p --logstore l
```

**Why**: `delete-index` removes the entire index and breaks query / SQL on that Logstore. The skill never chains it after other writes and must obtain explicit user confirmation.

### 7. Authentication — never expose credentials

#### CORRECT — Verify credential profile via default credential chain

```bash
aliyun configure list
```

#### INCORRECT — Passing AK/SK directly in the command

```bash
aliyun sls update-index \
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

### 8. API Names — verify exact sub-command

#### CORRECT

```
get-index        # OpenAPI Action: GetIndex
create-index     # OpenAPI Action: CreateIndex
update-index     # OpenAPI Action: UpdateIndex
delete-index     # OpenAPI Action: DeleteIndex
```

#### INCORRECT

```
GetIndex            # PascalCase is the Action name, not the CLI sub-command
getIndex            # Wrong casing
get_index           # Wrong separator (snake_case)
getindex            # Missing separator
describe-index      # Wrong verb — SLS uses get-, not describe-
put-index           # Wrong verb — use update-index
modify-index        # Not a real sub-command
get-log-index       # Not a real sub-command — use get-index
```

### 9. Region Parameter

#### CORRECT

```bash
--region cn-hangzhou
--region cn-shanghai
--region ap-southeast-1
```

#### INCORRECT

```bash
--region hangzhou       # Missing country prefix
--region cn-hangzhou-1  # Not a real region ID
--region-id cn-hangzhou # CLI global flag is --region, not --region-id
```

## Workflow Checklist

When the skill executes a write, it must satisfy all of:

- [ ] `aliyun configure list` was run and returned a configured profile.
- [ ] AI mode was enabled (`aliyun configure ai-mode enable`).
- [ ] `get-index` was called and the response was captured to a file before any write.
- [ ] Index body was written to `/tmp/<name>.json` (not inlined).
- [ ] `update-index` body is the **full** desired configuration, not a partial fragment.
- [ ] For `delete-index`, the user gave explicit confirmation and a backup file was written.
- [ ] AI mode was disabled at the end of the session (`aliyun configure ai-mode disable`).
