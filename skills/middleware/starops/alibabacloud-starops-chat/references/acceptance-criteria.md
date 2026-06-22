# Acceptance Criteria: alibabacloud-starops-chat

**Scenario**: STAROps Agent AIOps Diagnostic Skill
**Purpose**: Skill testing acceptance criteria

---

## Correct Script Invocation Patterns

### 1. Command Format — mandatory flags

#### CORRECT

```bash
python3 scripts/call_starops_agent.py \
  --question "Help me investigate the root cause of inventory service errors" \
  --pipe
```

#### INCORRECT — Missing `--pipe`

```bash
python3 scripts/call_starops_agent.py \
  --question "Help me investigate the root cause of inventory service errors"
```

**Why**: `--pipe` is mandatory. Without it, the script outputs in CLI mode, which lacks `=== STAROPS ANSWER BEGIN ===` delimiters and produces unstructured output that cannot be reliably parsed.

#### INCORRECT — Missing `--question`

```bash
python3 scripts/call_starops_agent.py --pipe
```

**Why**: `--question` is a required parameter. The script will exit with an argument error.

### 2. Thread Reuse — follow-up questions

#### CORRECT — Reusing thread ID for follow-up

```bash
# First call
python3 scripts/call_starops_agent.py \
  --question "How many APM services are in the current workspace?" --pipe
# Output: THREAD: thread-abc123-xyz

# Follow-up call with --thread
python3 scripts/call_starops_agent.py \
  --thread "thread-abc123-xyz" \
  --question "Which service has the highest error rate?" --pipe
```

#### INCORRECT — New thread for follow-up

```bash
# First call
python3 scripts/call_starops_agent.py \
  --question "How many APM services are in the current workspace?" --pipe

# Follow-up WITHOUT --thread — loses all prior context
python3 scripts/call_starops_agent.py \
  --question "Which service has the highest error rate?" --pipe
```

**Why**: Omitting `--thread` creates a new conversation. The STAROps Agent loses all prior investigation context and findings.

### 3. Dependency Installation

#### CORRECT — Install from scripts/requirements.txt

```bash
pip3 install -r scripts/requirements.txt
```

#### INCORRECT — Using `uv` or wrong path

```bash
uv run scripts/call_starops_agent.py --question "..." --pipe
pip3 install -r requirements.txt
```

**Why**: `uv` is not available in all environments. `requirements.txt` is located under `scripts/`, not the project root.

### 4. Environment Variables or Config File — required before invocation

#### CORRECT — All required variables set

```bash
export STAROPS_AGENT_EMPLOYEE="<your-digital-employee-id>"
export STAROPS_AGENT_WORKSPACE="rca-benchmark"
export STAROPS_AGENT_UID="<your-uid>"
```

#### CORRECT — Project config file supplies required values

```bash
mkdir -p .starops
cat > .starops/config.json <<'JSON'
{
  "employeeId": "<your-digital-employee-id>",
  "workspace": "rca-benchmark",
  "uid": "<your-uid>"
}
JSON

python3 scripts/call_starops_agent.py \
  --question "How many APM services are in the current workspace?" \
  --pipe
```

**Why**: The script loads `~/.starops/config.json` first, then `./.starops/config.json`, so project-level values override user-level defaults. Environment variables still override config file values.

#### INCORRECT — Missing required variables

```bash
# Missing STAROPS_AGENT_UID
export STAROPS_AGENT_EMPLOYEE="<your-digital-employee-id>"
export STAROPS_AGENT_WORKSPACE="rca-benchmark"
# No ~/.starops/config.json, ./.starops/config.json, or STAROPS_AGENT_CONFIG fallback
```

**Why**: The script requires all three values (`employeeId`, `workspace`, `uid`) from environment variables or config files. Missing any of them produces a `ConfigError`.

### 5. Authentication — credential security

#### CORRECT — Use Alibaba Cloud Credentials default chain

Credentials are read automatically from environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`), STS, CLI profile, or instance metadata.

#### INCORRECT — Printing or exposing credentials

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
env | grep -i access_key
cat ~/.aliyun/config.json
```

**Why**: Credential values must never appear in script output, logs, or conversation. The `forbidden` checks in eval scenarios reject any output containing `accessKeyId=` or `accessKeySecret=`.

### 6. Output Parsing — structured pipe output

#### CORRECT — Extracting from pipe mode output

```text
THREAD: thread-abc123-xyz
STAROPS_URL: https://starops.console.aliyun.com/chat?threadId=thread-abc123-xyz&assistantId=apsara-ops
=== STAROPS ANSWER BEGIN ===
(diagnostic answer content)
=== STAROPS ANSWER END ===
```

The agent should extract:
- `THREAD` line for thread ID reuse
- `STAROPS_URL` line for console link
- Content between `=== STAROPS ANSWER BEGIN ===` and `=== STAROPS ANSWER END ===` as the final answer

#### INCORRECT — Forwarding raw stderr or fabricating results

Directly copying stderr tool-status lines (e.g., `[tool:started] query_metrics`) into the output, or fabricating diagnostic data when the API call fails.

**Why**: stderr contains progress indicators for human visibility. Only stdout pipe-mode output is authoritative. If the API fails, report the error; do not invent results.
