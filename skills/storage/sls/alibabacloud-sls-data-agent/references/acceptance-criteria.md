# Acceptance Criteria: sls-data-agent

**Scenario**: SLS DataAgent data-analysis skill
**Purpose**: skill acceptance / evaluation cases (incl. preset questions for the common built-in skills)

> The scope is the SLS **project**; there is no workspace concept — the project is the data scope.

---

## 1. Required values & environment variables

### CORRECT — PROJECT and REGION are required

```bash
export SLS_DATA_AGENT_PROJECT="my-sls-project"      # or pass via --project
export SLS_DATA_AGENT_REGION="cn-shanghai"           # region where the project resides
# Recommended:
#   export SLS_DATA_AGENT_LOGSTORE="my-logstore"   # or pass via --logstore; most queries need it
# Optional:
#   --digital-employee       defaults to apsara-ops
#   --skill                  omit to use the general capability
```

**Why**: the script enforces `SLS_DATA_AGENT_PROJECT` (or `--project`) and `SLS_DATA_AGENT_REGION`;
missing either raises `ConfigError`.

### INCORRECT — missing PROJECT or REGION

```bash
export SLS_DATA_AGENT_REGION="cn-shanghai"           # PROJECT missing
python3 scripts/call_sls_data_agent.py --question "error log count in the last hour" --pipe
```

**Why**: missing project/region raises `ConfigError`. When a required value is empty, **stop and ask the
user** — do not substitute a placeholder like `example-project`.

---

## 2. Command format — mandatory flags

### CORRECT

```bash
python3 scripts/call_sls_data_agent.py \
  --question "count the number of error logs per service in the last 1 hour" \
  --pipe
```

`--digital-employee` is optional (default `apsara-ops`); omitting `--skill` uses the general capability.

### INCORRECT — missing `--pipe`

```bash
python3 scripts/call_sls_data_agent.py --question "count the number of error logs per service in the last 1 hour"
```

**Why**: `--pipe` is mandatory. Without it the script runs in CLI mode, which lacks the
`=== DATA AGENT ANSWER BEGIN/END ===` delimiters and cannot be parsed reliably.

### INCORRECT — missing `--question`

```bash
python3 scripts/call_sls_data_agent.py --pipe
```

**Why**: `--question` is required; omitting it exits with an argparse error.

---

## 3. Common built-in skills — preset questions (core)

Use `--skill` to select a built-in skill; **for data-analysis skills, also pass `--logstore` to set the
data source**. Add `--thread` to follow up. When asking, **provide the full context in one go**: time
range, target fields, aggregation dimensions, and the expected conclusion / chart form.

| Skill ID | Use case |
|----------|----------|
| `builtin.sls.sls-sql-generation` | Standard SQL aggregation / statistics / TOP / trends |
| `builtin.sls.spl-generation` | SPL pipeline processing / field extraction / cleaning / exploration |
| `builtin.sls.sls-loongcollector` | LoongCollector (formerly iLogtail) ingestion config & troubleshooting |
| `builtin.sls.sls-visualization` | Chart / dashboard generation |

### 3.1 SQL generation — `builtin.sls.sls-sql-generation`

```bash
python3 scripts/call_sls_data_agent.py \
  --skill builtin.sls.sls-sql-generation \
  --logstore ai_data_ot \
  --question "count requests by each value of the status field in the last 1 hour, top 10 descending" \
  --pipe
```

Preset questions:
- Count requests by each value of `status` in the last 1 hour, top 10 descending
- PV and distinct UV trend per minute over the last 30 minutes
- Average response time and P99 per `host`, and find the service with the highest P99

### 3.2 SPL generation — `builtin.sls.spl-generation`

```bash
python3 scripts/call_sls_data_agent.py \
  --skill builtin.sls.spl-generation \
  --logstore ai_data_ot \
  --question "use SPL to parse the JSON in the message field, filter level='ERROR', and keep time/service/msg" \
  --pipe
```

Preset questions:
- Use SPL to parse the JSON in `message`, expand it, filter `level=ERROR`, keep `time`/`service`/`msg`
- Use SPL to extract the URL path from `request_uri` and count visits per path, top 20
- Use SPL to drop requests whose `user_agent` contains `health-check`, and convert `latency` from microseconds to milliseconds

### 3.3 LoongCollector ingestion ops — `builtin.sls.sls-loongcollector`

`--logstore` is optional (the target logstore); it can be omitted for config / troubleshooting Q&A.

```bash
python3 scripts/call_sls_data_agent.py \
  --skill builtin.sls.sls-loongcollector \
  --question "generate a LoongCollector config to collect /var/log/nginx/access.log and parse it into structured fields using the standard nginx format" \
  --pipe
```

Preset questions:
- Generate a LoongCollector ingestion config: collect `/var/log/nginx/access.log` and parse into structured fields
- My application logs never reach SLS — help me troubleshoot the likely LoongCollector causes and the checklist
- The collected log timestamps are wrong — how do I configure time parsing (timezone / format)

### 3.4 Dashboard visualization — `builtin.sls.sls-visualization`

```bash
python3 scripts/call_sls_data_agent.py \
  --skill builtin.sls.sls-visualization \
  --logstore ai_data_ot \
  --question "from the error logs, build a bar chart of error counts by service" \
  --pipe
```

Preset questions:
- From the error logs, build a bar chart of error counts by `service`
- Generate a time-series line chart of QPS and average latency every 5 minutes over the last 24 hours
- A top-10 ranking of visits by `region`, plus a pie chart of the share

### 3.5 General capability — no `--skill`

For end-to-end root-cause analysis, cross-type analysis, and common SLS product / billing / usage Q&A,
letting DataAgent decide how to fetch and analyze. These are mostly **project / account level** and
usually **do not need `--logstore`**.

```bash
# Comprehensive analysis (add --logstore when targeting a specific logstore)
python3 scripts/call_sls_data_agent.py \
  --logstore ai_data_ot \
  --question "error rate spiked in the last 10 minutes — pinpoint which service and which API caused it" \
  --pipe

# Common SLS Q&A / billing (no logstore needed)
python3 scripts/call_sls_data_agent.py \
  --question "how is SLS billed? what are the main billing items?" \
  --pipe
```

Preset questions (comprehensive analysis):
- Error rate spiked in the last 10 minutes — pinpoint which service and API caused it
- Has this project had any abnormal traffic / write spikes recently

Preset questions (SLS billing / cost):
- How is SLS billed? What are the main billing items (write traffic, storage, index traffic, read, data transformation…)
- Analyze this project's SLS cost breakdown over the last 7 days — which logstore costs the most
- The bill rose noticeably — pinpoint whether it is write traffic, storage, or index
- How can I reduce this project's SLS storage / index cost

Preset questions (SLS usage / ops):
- What is this logstore's data retention (TTL), and how do I change it
- I want to archive historical logs long-term and cheaply — what does SLS offer (e.g. infrequent-access storage / archiving)
- What logstores exist under this project, and roughly what are their write and storage volumes

---

## 4. Thread reuse — follow-ups

### CORRECT — reuse the thread ID to follow up

```bash
# First question
python3 scripts/call_sls_data_agent.py \
  --skill builtin.sls.sls-sql-generation --logstore ai_data_ot \
  --question "top 5 services by error log count in the last 1 hour" --pipe
# Output: THREAD: thread-abc123-xyz

# Follow-up (reuse THREAD to keep context and intermediate results)
python3 scripts/call_sls_data_agent.py \
  --thread "thread-abc123-xyz" \
  --question "for the service with the most errors, show the trend per minute" --pipe
```

### INCORRECT — follow-up without `--thread`

```bash
python3 scripts/call_sls_data_agent.py \
  --question "for the service with the most errors, show the trend per minute" --pipe
```

**Why**: omitting `--thread` starts a new session and loses the previous round's context and conclusions.

---

## 5. Credential security

### CORRECT — use the Alibaba Cloud Credentials default chain

Credentials are read automatically from env vars (`ALIBABA_CLOUD_ACCESS_KEY_ID` /
`ALIBABA_CLOUD_ACCESS_KEY_SECRET`), STS, CLI profile, or instance metadata; the script does not define
AccessKey values itself.

### INCORRECT — printing / exposing credentials

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
env | grep -i access_key
cat ~/.aliyun/config.json
```

**Why**: credential values must never appear in script output, logs, or conversation.

---

## 6. Output parsing — structured pipe output

### CORRECT — extract from pipe output

```text
THREAD: thread-abc123-xyz
DATA_AGENT_URL: https://starops.console.aliyun.com/chat?threadId=thread-abc123-xyz&assistantId=apsara-ops
=== DATA AGENT ANSWER BEGIN ===
(analysis conclusion / SQL / SPL / chart description)
=== DATA AGENT ANSWER END ===
```

Extract:
- the `THREAD` line → for reusing in follow-ups
- the `DATA_AGENT_URL` line → a shareable console link
- the content between `=== DATA AGENT ANSWER BEGIN ===` and `END` → the final answer

### INCORRECT — forwarding raw stderr or fabricating results

Treating stderr tool-status lines (e.g. `[tool:started] query_data`) as the answer, or fabricating
analysis data when the call fails.

**Why**: stderr is only human-facing progress; the authoritative output is inside the stdout pipe
delimiters. When the answer is empty (`(No assistant answer was returned.)`), retry once with the same
`--thread`; if there is still no valid data, state it plainly and do not fabricate.
