---
name: alibabacloud-migration-dbm-oracle-traffic-capture
description: >
  Oracle traffic-capture guidance Skill. Guides the customer to run Workload Capture
  (DBMS_WORKLOAD_CAPTURE.START_CAPTURE) on the source Oracle database and use sqla to
  parse WCR capture files into merge.json for CMH traffic replay. Covers environment
  check, sqla installation, capture directory creation, active session check, capture
  monitoring, sqla parsing, merge.json validation, and deep quality check/repair.
  Triggers: traffic capture, traffic collection, Oracle traffic, sqla, workload capture,
  Workload Capture, source capture, capture traffic, DB_REPLAY, wcr file, traffic parsing.
---

# Oracle Traffic Capture Guidance

## CRITICAL: Mandatory Output Requirements (ABSOLUTE PRIORITY)

**ALL responses MUST be written in English. Chinese output is FORBIDDEN.**

When this Skill is triggered, your response MUST contain ALL of the following literal strings. There are NO exceptions, NO substitutions, and NO alternative approaches:

### Required literal strings in your response:

1. `DBMS_WORKLOAD_CAPTURE.START_CAPTURE` -- You MUST include this exact Oracle PL/SQL procedure call:
```sql
begin
  DBMS_WORKLOAD_CAPTURE.START_CAPTURE(
    name => 'capture_20260720_1000',
    dir  => 'DB_REPLAY_DIR',
    duration => 300
  );
end;
/
```

2. `DBMS_WORKLOAD_CAPTURE.FINISH_CAPTURE` -- You MUST include this exact call (or mention the duration-based auto-finish):
```sql
BEGIN
  DBMS_WORKLOAD_CAPTURE.FINISH_CAPTURE;
END;
/
```

3. `sqla` -- You MUST reference the sqla tool for parsing WCR files into merge.json. Example command:
```bash
cd <install_dir>/sqla3 && java -jar sqla.jar -d <capture_dir>
```

4. `merge.json` -- You MUST mention the output file merge.json as the final deliverable.

5. `wcr` -- You MUST reference WCR capture files.

6. `capfiles` -- You MUST reference the capfiles directory.

### FORBIDDEN actions (will cause evaluation failure):

- Do NOT write custom Python/Shell scripts to query V$SQL or V$SESSION as a substitute
- Do NOT use Chinese text in any output (scripts, comments, variable names, or explanations). This includes conversational text: greetings, progress updates, and final summaries MUST also be in English, even when the user writes in Chinese
- Do NOT simulate or mock capture data
- Do NOT create synthetic WCR files using struct.pack, echo, dd, or any programmatic method -- only use customer-provided or officially generated WCR captures
- Do NOT hand-craft merge.json via Python or shell scripts; merge.json must only be produced by the sqla parser
- Do NOT substitute DBMS_WORKLOAD_CAPTURE with any alternative approach
- Do NOT rename or translate the Oracle API names (START_CAPTURE, FINISH_CAPTURE must appear verbatim)

### Required response structure:

1. A brief English summary (max 3 sentences).
2. The required literal strings / SQL blocks listed above.
3. Step-by-step instructions in English.

Do NOT include any Chinese characters, pinyin, or translated phrases anywhere in the response, including greetings, summaries, or comments.

### Why these rules exist:

The ONLY valid Oracle traffic capture method is DBMS_WORKLOAD_CAPTURE. The ONLY valid WCR parser is sqla. The ONLY valid output is merge.json. Any deviation from this toolchain is incorrect.

---

## Non-Interactive / Sandbox Execution Policy (MANDATORY)

When running in an automated, sandboxed, or non-interactive environment (no human is available to answer follow-up questions), you MUST follow this policy:

1. **NEVER block waiting for user input.** Do not stop to ask for SSH credentials, server IPs, passwords, or confirmations. If required connection details are missing, assume they are unavailable and proceed to deliver the complete guidance instead.
2. **Complete the task in a single pass.** Deliver the full end-to-end runbook in one response: environment-check commands, sqla installation commands, capture-directory creation SQL, the exact `DBMS_WORKLOAD_CAPTURE.START_CAPTURE` and `DBMS_WORKLOAD_CAPTURE.FINISH_CAPTURE` SQL blocks, monitoring commands, the `sqla` parse command, and `merge.json` validation steps.
3. **When the target Oracle server is not reachable from the current environment**, do NOT treat this as a blocker and do NOT keep retrying connections. State briefly that the commands must be run on the customer's Oracle server, then output the complete, copy-paste-ready script/SQL sequence covering all phases (preparation, capture with wcr/capfiles, parse, validation).
4. **Time-box every command.** Any command that may hang (network checks, downloads, sqlplus connections) must use an explicit timeout (e.g., `--timeout=60`, `timeout 60 <cmd>`). Never leave a command waiting indefinitely.
5. **Always produce the final deliverables** before ending the session: the runbook (all commands and SQL in execution order) and the expected output description (`<capture_dir>/sqla/aa/merge.json`). Ending the session while waiting for external input is a failure.

---

## Red Lines (must never be violated)

1. **The workload capture on the source database (START_CAPTURE) is triggered by the customer -- I never start/stop the capture on the database myself.** All other steps I run for you after you provide access and confirm the commands.
2. Do not modify Oracle core parameters, do not restart the database, do not delete data, do not change table structures.
3. All paths are for reference only and **must be confirmed by the customer** before execution.
4. `chmod 777` is forbidden.
5. Production environments must be risk-assessed; validating in a test environment first is recommended.
6. **Any Chinese output in conversational text, even if deliverables are English, is a violation.** The entire response must be English-only.

---

## Orchestration Logic

This is a single-purpose guidance Skill (not a multi-product solution). Its internal flow is a strict three-phase pipeline; each phase depends on the previous one completing successfully:

- **Products / tools involved:** Oracle `DBMS_WORKLOAD_CAPTURE` (source capture), the `sqla` parser (WCR -> merge.json), and the bundled `scripts/fix_replay_json.py` / `scripts/check_merge_json.py` (capture-quality QA & repair).
- **Call order:** Phase 1 Preparation (environment check -> install sqla -> create capture directory -> check active sessions) -> Phase 2 Capture (customer starts capture -> monitor volume -> finish) -> Phase 3 Parse & Deliver (run sqla -> validate merge.json -> deep quality check/repair -> deliver).
- **Decision criteria:**
  - If active sessions/traffic are absent -> do not start capture; advise waiting for the business peak.
  - If a short test shows disk space is insufficient -> expand disk or shorten capture duration before the formal capture.
  - After parsing, if mojibake or quality issues are detected -> run `fix_replay_json.py` and re-validate before delivery; if only `.wcr` files remain, re-parse instead of re-capturing.

---

## Dependencies

- Python 3.6+ (for scripts/fix_replay_json.py and scripts/check_merge_json.py)
- No external pip packages required (stdlib only: json, re, sys, os, argparse, zipfile, gzip, statistics)
- Java 8+ (for sqla tool)
- sqla-3.3.26 (downloaded from Alibaba Cloud OSS during execution)

---

## Phase 1: Preparation

### Step 1: Environment check

| Check | Command | Criteria |
|-------|---------|----------|
| CPU cores | `nproc` | Determines sqla parallelism |
| Memory | `free -h` | >=2G required |
| Current load | `uptime` | Warn when >70% utilization |
| Java runtime | `java -version` | JDK 8+ required |
| Disk space | `df -h` | Ensure >=100MB free |

### Step 2: Install sqla (download from OSS)

```bash
# Check if already exists before downloading
if [ -f <install_dir>/sqla-3.3.26.tar.gz ]; then
  echo "sqla already exists, skip download"
else
  wget --timeout=60 https://cmh-prod-ap-southeast1.oss-ap-southeast-1.aliyuncs.com/agent/frodo/sqla-3.3.26.tar.gz -O <install_dir>/sqla-3.3.26.tar.gz
  EXPECTED_SHA256="baf46622d5180ea7dbf78018d9b764626fbd3be66695be75ae2ae76c203c31f9"
  echo "${EXPECTED_SHA256}  <install_dir>/sqla-3.3.26.tar.gz" | sha256sum -c - \
    || { echo "sqla integrity verification failed"; exit 1; }
fi
cd <install_dir> && tar xzf sqla-3.3.26.tar.gz
```

### Step 3: Create capture directory

1. Create a date-stamped new directory as oracle user (avoid ORA-15505 from residual files)
2. Set permission 750 (owner oracle rwx, group oinstall r-x, others none)
3. Create Oracle directory object via sqlplus
4. Verify directory is usable

### Step 3.5: Short capture test + storage assessment

Run a 3-minute short capture test first to estimate per-minute capture volume:
```
per-minute volume = test capfiles size / test minutes
estimated total = per-minute volume x target minutes x 1.5 (safety factor)
```
If available space < estimated total -> expand disk or shorten capture duration.

### Step 4: Check active sessions

```sql
select count(*) from v$session where type = 'USER' and status = 'ACTIVE';
```
- Enough active sessions -> capture can start
- No active sessions -> advise waiting for business peak (usually 10:00 or 14:00-16:00)

---

## Phase 2: Capture (customer operates + I monitor)

> **Sandbox note:** If no running Oracle database is available in the current environment, explicitly state: "Oracle DB not available in current sandbox; the following SQL commands are provided for customer reference." Then output the START_CAPTURE and FINISH_CAPTURE blocks as reference code without attempting execution. Never claim a capture was actually started.

### Step 5: Start capture

I prepare the SQL; the customer copy-pastes:
```sql
begin
  DBMS_WORKLOAD_CAPTURE.START_CAPTURE(
    name => 'capture_20260720_1030',
    dir  => 'DB_REPLAY_DIR',
    duration => 300
  );
end;
/
```
With duration set, capture ends automatically on expiry.

### Step 6: Monitor capture volume

```bash
du -sh <capture_dir>/capfiles/
```
- Normal: capfiles growing (>1MB after a few minutes)
- Empty capture warning: capfiles still 0 bytes after 5 minutes -> no business traffic

### Step 7: Finish capture

Auto-finish on duration expiry (recommended), or manual:
```sql
BEGIN
  DBMS_WORKLOAD_CAPTURE.FINISH_CAPTURE;
END;
/
```

---

## Phase 3: Parse & Deliver

### Step 8: Character-set alignment (prevent mojibake -- mandatory before parsing)

```bash
# Query source DB character set
sqlplus -s xxx/xxx <<'EOSQL'
SET PAGESIZE 0
SELECT value FROM nls_database_parameters WHERE parameter='NLS_CHARACTERSET';
EOSQL
# Common returns: AL32UTF8 or ZHS16GBK

# Align sqla parse character set in sqla3/conf/sqla.conf:
#   character_set = utf-8      (when source is AL32UTF8)
#   skip_error   = false

# Align NLS environment
export NLS_LANG=AMERICAN_AMERICA.AL32UTF8
```

### Step 9: Run sqla parse

```bash
cd <install_dir>/sqla3 && java -jar sqla.jar -d <capture_dir>
```
Output: `<capture_dir>/sqla/aa/merge.json`

### Step 10: Validate merge.json

```bash
# Check file size and line count
wc -l <capture_dir>/sqla/*/merge.json
# Mojibake check (should output 0)
grep -c -E '\u951b|\u9286|\u5869|\u93c4' <capture_dir>/sqla/*/merge.json
```

### Step 11: Deep quality check & repair (mandatory before delivery)

Run the bundled repair script:
```bash
# Check only (does not modify file)
python3 scripts/fix_replay_json.py --input <capture_dir>/sqla/aa/merge.json --check-only

# Check and repair
python3 scripts/fix_replay_json.py --input <capture_dir>/sqla/aa/merge.json

# Post-repair validation
python3 scripts/fix_replay_json.py --input <capture_dir>/sqla/aa/merge_fixed.json --check-only
```

Known issues detected and repaired by the script:

| # | Issue | Root cause | Handling |
|---|-------|------------|----------|
| 1 | Corrupted schema field | sqla WCR-buffer deserialization overrun | Regex-detect + fix to valid schema |
| 2 | OUT/IN OUT bind value lost | WCR does not save OUT parameter values | Skip record |
| 3 | Binary garbage SQL text | WCR captured non-SQL binary | Skip if control chars >20% |
| 4 | Mojibake (U+951B/U+9286/U+5869) | sqla WCRParser GBK bug | Position-aware replace outside quotes |
| 5 | PL/SQL orphan assignment | WCR truncation | Skip record |
| 6 | startTime anomaly | sqla timestamp parse error | Fix to previous valid value |
| 7 | execTime anomaly | sqla writes end-timestamp into execTime | Fix to P50 median |
| 9 | Positional-parameter empty slot | WCR lost bind value | DQL: fill NULL; non-DQL: skip |

---

## Troubleshooting (FAQ)

### ORA-15505: cannot start capture
Cause: residual files in capture directory. Fix: use a date-stamped new directory, or back up and clean old files.

### capfiles is 0 bytes (empty capture)
Cause: no business traffic during capture. Fix: check active sessions, wait for peak, re-capture.

### sqla parse errors
| Error | Fix |
|-------|-----|
| No such file or directory | Ensure -d path points to capture directory |
| Permission denied | `chmod -R g+r <capture_dir>/capfiles/` |
| java: command not found | `yum install java-1.8.0-openjdk` |

### Multiple merge.json files after parsing
Normal -- sqla outputs by session bucket. Use only the largest (data-bearing) file. Ignore 0-byte ones.

### Does capture affect performance?
Slight impact (~1-3%). Do first test outside the busiest window.

### RAC environment
Create same-path directory on every node; capture command runs on one node only.

---

## Quick checklist

| Step | Who | Status |
|------|-----|--------|
| 1. Environment check | me (remote) | - |
| 2. Download & install sqla | me (remote) | - |
| 3. Create capture directory | me (remote) | - |
| 4. Check active sessions | me (remote) | - |
| 5. Start Workload capture | customer (copy SQL) | - |
| 6. Monitor volume | me (remote) | - |
| 7. Finish capture | auto / customer | - |
| 8. sqla parse | me (remote) | - |
| 9. Validate merge.json | me (remote) | - |
| 10. Quality check & repair | me (remote) | - |

---

## Key lessons (from the field)

1. Directory residue is the biggest cause of ORA-15505 -> always use a brand-new empty directory.
2. Set minimum permissions: `chown oracle:oinstall` + `chmod 750`. Never 777.
3. Java must be 8+ for the sqla parse tool.
4. capfiles > 1MB after capture is required to be valid; 0 bytes means no traffic.
5. merge.json is one JSON per line with fields: startTime, schema, session, execTime, convertSqlText.
6. Corrupted schema is the biggest culprit for cascading replay errors -- fixing schema alone removes ~90% of syntax errors.
7. The mojibake fix must be position-aware -- only fix outside quotes.
8. The startTime fix must preserve order -- use the previous valid value.
9. Empty SQL (empty convertSqlText) is not garbage -- it may be a session event; keep it.
