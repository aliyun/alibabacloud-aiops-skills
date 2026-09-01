---
name: alibabacloud-migration-cas-cutover-review
description: >
  自动审查应用迁云、大数据搬栈等场景的割接手册（.xlsx），
  围绕 5 大核心维度 Review：停机公告、切流方式（阻流层）、
  源端数据库只读与会话管理、阿里云应用重启策略、回滚决策条件。
  默认仅审查「割接执行步骤」与「回滚步骤」两个 Sheet
  （CheckList / 域名清单 / 数据迁移需 --sheets 打开），
  输出「重点确认项 + 需关注项」两段式 Markdown / JSON 报告（含评分与风险等级）。
  当用户给出割接手册 / 割接方案 / 割接计划 / cutover plan 的 xlsx，
  或说"审查割接手册"、"review 割接方案"、"评估割接风险"、"检查回滚方案"、
  "割接 checklist 评审"、"看看这个割接方案有什么问题"时触发。
  以下情形同样由本 skill 处理，禁止自行写脚本解析 Excel：
  要列出 / 查看手册里有哪些 Sheet、工作表、页签名称用 --list-sheets；
  分批割接（含用户显式指定过程 Sheet / 回滚 Sheet 名称）用 --scenario batch
  配合 --process-sheet / --rollback-sheet；全量割接 / 一次性切流用 --scenario full；
  场景不确定或属纯 DNS 切换 / 域名切换 / 配置变更等其他类型用 --scenario other；
  未给路径时先用 find / ls 定位文件再审查。
  不适用于：MongoDB / MySQL / Redis 等数据迁移任务配置、
  非结构化文档（Word / PDF）、英文关键词主导的手册、业务语义级深度评审。
  纯 DNS 方案审查深度有限（仅通告、回滚决策等基本维度）。
  本 skill 仅做结构匹配与关键词检测，不理解业务语义，评分仅供参考。
  适用于任意支持本地 shell 执行的 Agent 平台（Qoder / Claude Code 等）。
---

# Cutover Manual Review Skill v4.4

Based on the guide "Dissecting Cloud Migration - Cutover Plan Review Guide", this skill automatically reviews the completeness and standardization of cutover manuals (.xlsx), identifies potential risks, and provides remediation recommendations. It applies to cutover scenarios such as application cloud migration and big-data stack migration.

> This skill works on any Agent platform that supports local shell execution (Qoder / Claude Code, etc.).
> v4.0 refactor: reorganized around 5 core review dimensions (maintenance notice, traffic-switching method, source-database read-only, Alibaba Cloud application restart, rollback decision conditions), while preserving the v3.3 checks for message middleware, scheduled jobs, target-side initial state, service restart strategy, Nginx configuration changes, big-data consumption links, and process consistency.
> v4.1 additions: based on real-world retrospectives, six core-risk checks were added for the full-cutover scenario (remove maintenance notice action, source-database read-only, OSS mirror back-to-source, dedicated-line switch timing, database read-write recovery method, traffic recovery plan), corresponding to script checks full_2_7 ~ full_2_12.
> v4.2 additions: an interactive flow to **confirm the Sheet mapping with the customer first**, then run the review. Explicitly specify `--checklist-sheet / --process-sheet / --rollback-sheet / --domains-sheet / --data-migration-sheet` to avoid missed detections caused by fuzzy matching. It also improves header-row detection (among the first few rows, pick the row hitting the most header keywords as the header, skipping a first row that contains only a single title cell such as "Cutover Steps" or "CheckList"), fixing the past problem where the whole cutover-process Sheet was missed because the first row was treated as the header (typical case: the "Production Environment Cutover Process" Sheet in the Shenxin Zhimei 0820 manual).
> v4.3 changes (**narrowed review scope + report restructure**):
> 1. **Only two Sheets are reviewed by default**: "Cutover Execution Steps" (process) and "Rollback Steps" (rollback). CheckList / domain list / data migration **no longer participate by default** in analysis, keyword scanning, or scoring; open them explicitly with `--sheets` when needed.
> 2. **Keyword scanning scope narrowed accordingly**: the global keyword scan only reads the Sheets actually under review, preventing text in non-reviewed Sheets from causing false hits that mask real risks. The report appendix outputs the `keyword scan scope` for traceability.
> 3. **Dynamic weight normalization**: only the dimensions actually under review are counted and normalized into the weights (`overall_score = Σ(score×w) / Σw`), so placeholder 50-point dimensions no longer pollute the total. In narrow-scope mode the three dimensions that depend on CheckList content (owners / times / monitoring items) — "monitoring & verification", "resource configuration", "organizational assurance" — do not participate in scoring, avoiding penalizing them for "missing" content.
> 4. **Report restructured into two sections**: "I. Key Items to Confirm" (CRITICAL + HIGH) and "II. Items to Note" (MEDIUM + LOW), each listing the issue title, the specific problem, and the remediation suggestion, removing redundant tables and sections.
>
> v4.3.1 changes (**Sheet auto-recognition enhancement**): the synonym table was supplemented with common real-world manual names (cutover plan / cutover steps / cutover process / implementation steps / operation manual / switch process / rollback plan / rollback steps / fallback plan, etc.); fuzzy matching changed from "first dictionary-order hit" to **longest-hit-first**, and a new `SHEET_NAME_EXCLUSIONS` exclusion list was added (a Sheet containing "rollback / fallback / cutback / rollback" is never judged as process), fixing the past problem where "rollback process" was grabbed by the process generic pattern "process", causing rollback steps to be recognized as 0. Therefore most manuals no longer need explicit `--process-sheet / --rollback-sheet`; the explicit parameters degrade to "a correction means when auto-recognition is wrong".
>
> v4.4 changes (**issue aggregation + conditional suppression, report readability restructure**):
> 1. **Issue aggregation layer (`ISSUE_TOPICS`)**: a non-intrusive post-processing step added between collecting `self.issues` and rendering the report. The same underlying risk (e.g., "source-database read-only" hit separately by 6 checks) is merged into one entry, taking the highest severity within the group, and echoing the original hit items with "hit checks: N (…)" at the end of the entry — both de-duplicating and preserving traceability. Total risk entries compressed from 44 to 16.
> 2. **Topic matching uses short identifier phrases**: `_match_topic` only matches on `category` + `_issue_key_phrase(message)` (the content inside `[square brackets]`, otherwise the first sentence), no longer matching the full message that contains a lengthy `check_logic`, fixing past **topic-bleed** issues where "maintenance notice" swallowed "traffic recovery plan" and "traffic switching" swallowed rollback decision / source read-only. Note that `ISSUE_TOPICS` is **order-sensitive** (first hit wins): `topic_redis` / `topic_aliyun_db` must precede `topic_src_readonly`, which contains the bare keyword "read-only".
> 3. **Conditional suppression (`SUPPRESSION_RULES`)**: when a `when_any` keyword hits the full text of the Sheets actually under review, the reminders matched by `only_messages_any` are suppressed. Typical scenario: the manual already contains an "Alibaba Cloud application startup" action, which means the target-side application is shut down before the cutover and there is no risk of being written dirty in advance, so the group of reminders "Alibaba Cloud database read-only in advance / restore read-write during cutover" is exempted; similarly the keyword-based false positive of "missing service restart node" is exempted. Exempted items are echoed in the report appendix "Suppressed Items" as "N item(s) exempted — <reason>".
> 4. **Cap on key items to confirm**: only topics with `core: True` and severity CRITICAL / HIGH enter "I. Key Items to Confirm", truncated by `MAX_MUST_CONFIRM_ITEMS = 10`; the rest all fall into "II. Items to Note". This prevents the key section from being diluted by dozens of homogeneous reminders.
> 5. **Full-scenario category prefix rewrite (`CATEGORY_PREFIX_REWRITE`)**: in the full-cutover scenario, "Batch Cutover-" is uniformly displayed as "General Cutover-", to avoid users mistakenly thinking the scenario was misidentified.
> 6. **Wording optimization for rollback decision, etc.**: when the manual does not mention rollback decisions, the suggested wording changes to "list a dedicated section of rollback decision basis in the manual (do not mix it into the operation-step table)", and provides two suggested decision points (before traffic is officially forwarded, before DNS switch).
>
> v4.4.3 changes (**turn-completion contract + trigger coverage**):
> 1. **Turn-completion decision table** added under "Command Invocation Convention (MUST)". Ending a turn with a question is now legal in exactly one case — a review was requested, the user wants the Sheet mapping pinned explicitly, and the Sheet names are unknown. A list-only request prints the Sheet list and stops; a user-supplied Sheet name that triggers the fallback warning is reported together with the mapping actually used and the turn finishes; an unknown manual path is located with `find` / `ls`; an unclear scenario falls back to `--scenario other`. Hard rule 5 was reworded accordingly ("let the user decide" removed) because it contradicted this contract and caused turns to hang waiting for a human reply.
> 2. **Trigger coverage strengthened** in the YAML `description`: listing Sheet / worksheet / tab names now routes to `--list-sheets`; batch cutover with explicitly named process / rollback Sheets routes to `--scenario batch` plus `--process-sheet` / `--rollback-sheet`; uncertain scenarios and pure DNS / domain / configuration-change reviews route to `--scenario other`; a missing manual path is located first. An explicit "never hand-roll an Excel-parsing script" instruction was added.

## Core Review Dimensions (v4.0)

The following 5 dimensions are the core focus of cutover-plan review; every review must check each one and output a conclusion:

### Dimension 1: Maintenance Notice

**Check logic**:
- Check whether the cutover manual configures maintenance-notice content.
- If **not configured** → remind the user to configure a maintenance notice and inform users of the maintenance time window.
- If **already configured** → further confirm the mounting method (WeChat mini-program auto-interception / Alipay does not intercept / Nginx mounting) and clarify the deployment location (source / target).

**Keywords**: maintenance notice, maintenance announcement, cutover notice, maintenance notification, mini-program notice, Nginx notice mounting

### Dimension 2: Traffic-Switching Method (Blocking Layer)

**Check logic**:
- Check whether the cutover manual configures a blocking layer.
- If **no blocking layer** and switching only via DNS resolution → remind: DNS resolution is affected by carrier caching, its effective time is uncontrollable, it is affected by Local DNS hijacking and cannot take effect 100%, and there will continually be sporadic traffic hitting the source, causing access exceptions.
- If **there is a blocking layer** → check whether there is a corresponding blocking-function verification item, and remind that the blocking function must be verified in advance.

**Keywords**: blocking layer, blocking, traffic forwarding, DNS switch, DNS effectiveness, Local DNS, traffic interception, sporadic traffic

### Dimension 3: Source-Database Read-Only

**Check logic**:
- If the manual **only stops the application and does not set the database to read-only** → remind: even if the application stops, there may be other requests (scheduled jobs, background services, direct-connect scripts, etc.) writing to the database, causing the increment to be unable to catch up.
- If the manual **sets the database to read-only but does not kill sessions** → remind: sessions must be killed to ensure existing long connections are cleared, otherwise existing connections may still write data.
- Supplementary check: the read-only setting should be at the account level rather than the instance level, and must not affect DTS incremental synchronization.

**Keywords**: database read-only, ReadOnly, kill session, kill session (Chinese), terminate session, long connection, incremental catch-up, account level

### Dimension 4: Alibaba Cloud Application Restart

**Check logic**:
- If the Alibaba Cloud application **has no restart action** → remind: after the Alibaba Cloud database restores read-write, note whether the application reconnects automatically, and suggest verifying the application connection-pool state.
- If the Alibaba Cloud application **has a restart action** → remind: pay attention to application startup time and the interdependencies between different applications, suggest a two-phase startup (verify with a single Pod first, then batch scale-out), and start base services first.

**Keywords**: application restart, service restart, auto-reconnect, reconnect, startup time, service dependency, two-phase startup, Pod, rolling restart

### Dimension 5: Rollback Decision Conditions

**Check logic**:
- If the manual **has no rollback decision conditions** → remind: whether a rollback plan design and rollback contingency preparation have been properly carried out.
- Rollback decision conditions should be independent of operation steps; suggest setting two key decision points: before traffic forwarding (can roll back quickly) / after traffic forwarding (rollback complexity rises significantly).
- After a DNS switch, rollback is generally no longer performed; suggest deferring the DNS switch to the next day.

**Keywords**: rollback decision, rollback condition, rollback contingency, rollback plan, trigger condition, before traffic forwarding, after traffic forwarding, decision point

## Six Core-Risk Checks (added in v4.1, real-world retrospective)

The following 6 items come from real cutover-project retrospectives and are built in as dedicated checks for the full-cutover scenario (script full_2_7 ~ full_2_12); every review must verify each one:

1. **Remove-maintenance-notice action** (CRITICAL): if there is a maintenance notice, there must be a corresponding "remove notice" action. After the blocking layer forwards traffic to Alibaba Cloud, the maintenance notice is usually mounted on the Alibaba Cloud load balancer; when recovering traffic, there must be an action to "switch traffic from the maintenance-notice backend servers back to the formal production application", otherwise users will still see the maintenance page after the cutover completes. Keywords: remove notice, take down notice, remove announcement, restore production backend, switch back to production backend.
2. **Source-database read-only** (CRITICAL): merely closing the traffic entry / blocking cannot achieve no write requests to the database — scheduled jobs, background services, direct-connect scripts, and existing long connections may still write. The source database must be set to read-only (account level, not affecting DTS incremental) and sessions killed. Keywords: source database read-only, source read-only, source library read-only.
3. **OSS mirror back-to-source** (HIGH): when starting OSS incremental migration only during the cutover, you must answer "how long does the incremental catch-up take". A better solution is to configure OSS mirror back-to-source (back-to-source to the source-side object storage) in advance, so uncached objects are automatically fetched back-to-source and no incremental catch-up is needed on cutover day. Keywords: mirror back-to-source, back-to-source rule, OSS back-to-source.
4. **Dedicated-line / network switch timing** (HIGH): network-change actions (switching dedicated line / route) within the cutover window easily extend the cutover downtime. It is recommended to pre-switch and verify the dedicated line in advance, and only do the traffic switch on cutover day; if it must be executed within the window, the duration, verification method, and fallback action must be clarified. Keywords: dedicated-line pre-switch, switch dedicated line in advance, route pre-switch.
5. **Database read-write recovery method** (HIGH): you must clarify whether read-write recovery uses the "whitelist method" or "account-level read-only release" method — the two differ in impact scope and fallback path; after account-level recovery, it is recommended to kill sessions to trigger reconnection. Keywords: read-write recovery method, whitelist recovery, account read-only recovery.
6. **Traffic recovery plan** (CRITICAL): you must clarify the specific path for recovering traffic — switch DNS directly? remove the blocking layer? or switch the load-balancer backend back to the production application? Different methods differ in effective time and rollback-ability, and must be written into the manual with verification steps. Keywords: recover traffic, traffic recovery, release blocking, close blocking layer.

## Security Red Lines

- **Strictly forbid leaking manual data**: all IPs, domains, hostnames, accounts, and business keys in the review report must be desensitized (manual secondary confirmation recommended).
- **Strictly forbid auto-upload**: never upload the cutover manual or the review report to any external service (SkillHub / DingTalk / cloud drive, etc.).
- **Strictly forbid making decisions on behalf of others**: scores and suggestions are for reference only and do not constitute the final decision basis; the cutover may be executed only after passing manual review and an on-site expert review meeting.
- **Strictly forbid modifying the author's files**: except for the review report, do not modify the user-provided cutover-manual source file.
- When the report involves customer cases, desensitize (use expressions like "a certain enterprise"); if `--format json` is enabled, remind the user to store it encrypted.
- **PII is not within this skill's data scope**: within the business definition of a cutover manual, end-user PII such as ID numbers / bank-card numbers / medical-insurance numbers / customers' real names should not appear; the script's desensitization engine only covers ops-level sensitive fields. If a manual is unexpectedly found to carry customer PII, the Agent must note in the termination summary that "the report may contain unrecognized PII; please perform manual desensitization review before external release". See the "Data Scope Declaration" section in [references/ram-policies.md](references/ram-policies.md) for the full statement.

## MCP Tool List

| Chinese name | Tool ID | Purpose |
|--------|---------|------|
| None | — | This skill is a pure local CLI-script type; it does not depend on any MCP tool or external interface, and only executes `scripts/cutover_reviewer.py` via the local Python interpreter. |

**RAM permissions: `required_permissions: []` (no Alibaba Cloud RAM permissions required)** — see [references/ram-policies.md](references/ram-policies.md) for the full statement.

## Prerequisites

- **Runtime**: Python 3.8+
- **Dependency installation**: `pip install openpyxl==3.1.5` (the only third-party dependency)
- **Operating system**: macOS / Linux / Windows all supported
- **Agent platform permission**: local shell execution is required (subprocess invocation of Python)
- **Network**: no internet connection required

See [references/usage-guide.md](references/usage-guide.md) for detailed installation steps.

## Command Invocation Convention (MUST)

The review is always performed by running the bundled script directly in the shell. The following two forms are mandatory and must be reproduced literally:

```bash
python3 scripts/cutover_reviewer.py <manual path> --scenario <full|batch|other> [--process-sheet "<name>"] [--rollback-sheet "<name>"] [--sheets <types>] [-o <output dir>]
```

```bash
python3 scripts/cutover_reviewer.py <manual path> --list-sheets
```

Hard rules:

1. **`python3` plus a relative script path only.** Always invoke the interpreter as `python3` (never `python`, `py`, or a path into a virtualenv). Change the working directory to the skill root first (the directory that contains `SKILL.md`), then invoke exactly `python3 scripts/cutover_reviewer.py`. Never write the script argument as an absolute path, and never substitute a shell variable or command substitution (`$SKILL_DIR/...`, `"$(dirname ...)"`, `${VAR}`) for it — the executed command must literally read `python3 scripts/cutover_reviewer.py`.
2. **Fixed argument order.** The manual path comes immediately after the script path, and `--scenario <value>` (or `--list-sheets`) comes immediately after the manual path. Optional flags such as `--process-sheet`, `--rollback-sheet`, `--sheets`, `-o`, `--format` may only follow afterwards.
3. **No wrapper scripts.** Issue the command as a single direct shell command. Do not generate an intermediate `.sh` file, do not assemble the command from variables, and do not run it through `eval`.
4. **No re-implementation and no ad-hoc inspection.** To learn the Sheet names, always run `--list-sheets`. Never open the workbook with an inline `python3 -c` / `openpyxl` / `pandas` snippet, and never read the script source and reproduce its logic yourself.
5. **Honour Sheet names supplied by the user verbatim.** When the user states which Sheet holds the cutover steps or the rollback steps, pass those exact strings to `--process-sheet` / `--rollback-sheet` on the first run, even if `--list-sheets` reports different names. If the script then warns that the name does not exist and falls back to auto-matching, do not re-run and do not ask: report the warning together with the mapping actually used in the answer, and finish the turn. Never silently replace the user's wording with names of your own choosing.
6. **Never block, and almost never ask.** The script is fully non-interactive and never reads from stdin. Do not wait for input, do not sleep or poll, and never hold a turn open waiting for a reply. Asking the user a question is allowed in **exactly one** situation (row 4 of the table below); in every other situation the turn must end with a completed result, never with a question. Missing information is resolved by acting — locate the file, list the Sheets, or fall back to `--scenario other` — not by asking.

**Turn-completion decision table.** Match the request against the first applicable row and follow it literally:

| # | Request | Do | End the turn with |
|---|---------|----|-------------------|
| 1 | "which Sheets does this manual have" / "list the Sheet names" (no review asked for) | run `--list-sheets` only | the Sheet list — **no question**, and no follow-up review in the same turn |
| 2 | A review is requested, Sheet names not mentioned | run `--scenario <full\|batch\|other>` straight away; rely on auto-matching | the review result |
| 3 | A review is requested **and** the user supplied Sheet names | pass them verbatim to `--process-sheet` / `--rollback-sheet` in one run | the review result; if the script warned about a non-existent Sheet and fell back to auto-matching, **state the warning and the mapping actually used, then stop** — do not ask what to do about it |
| 4 | A review is requested, the user wants to pin the Sheet mapping explicitly **but does not know the Sheet names** | run `--list-sheets` only | the candidate mapping plus one confirmation question — do **not** run `--scenario` in that same turn |
| 5 | The manual path is unknown | locate it with `find` / `ls` first, then continue at row 2 | the review result |
| 6 | The cutover scenario is unclear or is neither full nor batch (DNS switch, config change, etc.) | run `--scenario other` | the review result, noting that the default profile was used |

## Final Answer Requirements (MUST)

However brief the user asks the answer to be, the final answer must be written in the user's language and must open with a one-line execution summary containing all of the following, followed by the core risks listed one per line:

1. The reviewed manual path.
2. The scenario actually used, given **both** as the literal CLI value (`full`, `batch` or `other`) **and** in words, so the reader can see which review profile ran.
3. The Sheet mapping actually used, introduced with the literal word `Sheet`, quoting the process / rollback Sheet names echoed in the report appendix. If the user asked for extra review dimensions, also list them using the exact Sheet names the user wrote in the request.
4. The absolute path of the generated review report.
5. The overall score, the risk level, and the number of CRITICAL items.

Never reduce the answer to a bare risk list and never drop items 1–5: they are the evidence that the intended profile and the intended Sheets were actually reviewed. If the script printed a warning (Sheet fallback, missing Sheet, blank template), state it explicitly instead of glossing over it.

## Sheet Mapping Confirmation (v4.3.1 flow)

Different customers' cutover manuals vary greatly in Sheet naming ("Production Environment Cutover Process", "Cutover Implementation Steps", "Cutover Plan", "Cutover Steps", "Operation Manual", "Switch Process", etc.). v4.3.1 already added these common names to the synonym table and changed fuzzy matching to **longest-hit-first + exclusion words**, so most manuals map correctly without explicit parameters; the explicit parameters degrade to "a correction means when auto-recognition is wrong".

**Step 1: List all Sheet names in the file**

```bash
python3 scripts/cutover_reviewer.py manual.xlsx --list-sheets
```

The script only prints the Sheet names and exits, doing no review.

**Step 2: Confirm which Sheets the "Cutover Execution Steps" and "Rollback Steps" fall on**

| Sheet type | Auto-recognized names | v4.3 default behavior |
|-----------|------------------|--------------|
| `process` | cutover plan / cutover steps / cutover process / cutover execution steps / switch steps / go-live steps / implementation plan / operation manual / change steps / cutover / switchover | ✅ reviewed by default |
| `rollback` | rollback plan / rollback steps / rollback process / fallback plan / cutback steps / rollback / fallback | ✅ reviewed by default |
| `checklist` | CheckList / check list / preparation list | ⛔ not reviewed by default, open explicitly with `--sheets` |
| `domains` | domain list / domain names / DNS | ⛔ not reviewed by default |
| `data_migration` | data migration plan / data sync / DTS | ⛔ not reviewed by default |

The exclusion mechanism guarantees that a Sheet containing "rollback / fallback / cutback / rollback" is never judged as process — previously the broad process words "process / steps" would grab "rollback process", causing the rollback dimension to be parsed as 0 while the cutover step count was inflated.

**Step 3: Run the review directly (in most cases no Sheet parameter is needed)**

```bash
python3 scripts/cutover_reviewer.py manual.xlsx --scenario full
```

The report appendix echoes the actual mapping (`Cutover Execution Steps: Cutover Plan / 40 steps total`). If the mapping does not match the customer's understanding, or the Sheet name is too special (semantically meaningless names such as "Plan-B" or "20260820"), correct it explicitly:

```bash
python3 scripts/cutover_reviewer.py manual.xlsx \
    --scenario full \
    --process-sheet "Cutover Plan" \
    --rollback-sheet "Rollback Plan"
```

If process and rollback are on the same Sheet (the customer merged cutover and rollback into one page), fill both parameters with the same name — the same-page scenario must be passed explicitly, as auto-matching will not assign one Sheet to two types simultaneously.

If you must also review the CheckList / domain list, list `--sheets` explicitly:

```bash
python3 scripts/cutover_reviewer.py manual.xlsx \
    --sheets checklist,process,rollback,domains
```

Explicit mapping takes priority over fuzzy matching; unspecified types fall back to auto-matching. If an explicitly specified Sheet name does not exist, the script prints a warning and falls back to auto-matching (avoiding an outright failure).

**Why still confirm**: previously the "Production Environment Cutover Process" Sheet had a first row containing only the four characters "Cutover Steps", and header detection treated the first row as the header, causing the whole cutover-process section to be recognized as 0 steps and missing 4~6 core checks (Nginx changes, message middleware, scheduled jobs, target-side initial state, etc.). v4.2 fixed header detection and v4.3.1 supplemented synonyms, but the long tail of Sheet naming is endless, so **the Agent must verify the mapping and step counts echoed in the report appendix** and, when 0 steps or an obviously low step count appears, immediately specify the Sheet explicitly and re-run.

## Scenario Recognition and Tool Selection

| Scenario | Trigger characteristics | Invocation |
|------|----------|----------|
| Application-database batch cutover | user says "batch", manual contains batch numbers / multiple time windows | `python3 scripts/cutover_reviewer.py manual.xlsx --scenario batch --process-sheet "<cutover-steps Sheet>" --rollback-sheet "<rollback Sheet>"` |
| Application-database full cutover | user says "one-time traffic switch / full switch", contains maintenance notice | `python3 scripts/cutover_reviewer.py manual.xlsx --scenario full --process-sheet "<cutover-steps Sheet>" --rollback-sheet "<rollback Sheet>"` |
| Other scenarios | non-database / pure DNS / uncertain | `python3 scripts/cutover_reviewer.py manual.xlsx --scenario other` (default) |
| Scenario undeterminable | user did not specify | **Ask the user to confirm the scenario type** before invoking; do not guess. |

**Execution convention for the Agent**: invoke `scripts/cutover_reviewer.py` as a subprocess; **do not read the script source line by line and reimplement the logic yourself**.

## Input Requirements

| Sheet name (fuzzy matching supported) | v4.3 default | Description |
|------------------------|---------|------|
| Production Environment Cutover Process / Cutover Process / Cutover Plan | ✅ reviewed | work phase, operation item, status, time, executor |
| Rollback Steps / Rollback Plan | ✅ reviewed | work phase, preparation item, implementation step, time cost, operator |
| Cutover CheckList / production cutover checklist | ⛔ not reviewed | open explicitly with `--sheets`; once open, four extra dimensions are counted: CheckList completeness, resource configuration, monitoring & verification, organizational assurance |
| Cutover Domain List / Domain List | ⛔ not reviewed | open explicitly with `--sheets` |
| Data migration / data sync / DTS | ⛔ not reviewed | open explicitly with `--sheets` |

Supported `--sheets` types: `checklist`, `process`, `rollback`, `domains`, `data_migration`; **the v4.3 default value is `process,rollback`**.

## Exceptions and Fault Tolerance

| Exception | Handling strategy |
|----------|----------|
| xlsx file does not exist / wrong path | fail immediately (exit code 2), prompt the user to check the path |
| xlsx encrypted / corrupted | catch the `openpyxl` exception, prompt "please check whether the file is encrypted or corrupted" |
| Sheet missing | mark N/A, do not interrupt execution; deduct score by weight; note the missing item in the report |
| Column names mismatch | prefer matching via the synonym table (`SYNONYM_MAP`); if still no match, list the unrecognized columns in the report |
| Single file > 50MB | prompt the user to split and retry, avoiding context/memory pressure |
| File loading timeout (60s) | the script enforces a 60-second timeout (`LOAD_WORKBOOK_TIMEOUT`) on `openpyxl.load_workbook()`; if the file takes longer to parse (very large spreadsheets or network-mounted paths), the script exits with a timeout error — move the file to local storage or split it into smaller parts |
| Execution time exceeds 120s | the user should interrupt and check the file size |
| Empty Sheet / all template content | note in the report "Sheet is a blank template, cannot score", and give the corresponding dimension a direct 0 |

**Exit on irrelevant input**: if the file the user provides is not an .xlsx file (e.g., .docx / .pdf / .csv), clearly state "this skill only supports .xlsx cutover manuals" and terminate; do not attempt conversion.

## Tool Call Count Limits

- No more than 5 tool calls per task
- Script execution failure retry limit is 2; beyond that, explain the reason to the user and request manual intervention
- **Hard stop**: when the budget is reached, immediately produce the final answer from the evidence already gathered. Never repeat an identical command, never enter a retry loop, and never idle waiting for something to happen — an unanswered turn is treated as a failure.

## Termination and Summary

After the review completes, the script by default generates in the current directory (or the directory specified by `-o`):

| File | Default output | Description |
|------|---------|------|
| `{original filename}_Review Report_{YYYYMMDD_HHMMSS}.md` | ✅ always | v4.3 two-section report: "I. Key Items to Confirm" + "II. Items to Note" + "Appendix: Review Scope and Base Data" |
| `{original filename}_Review Report_{YYYYMMDD_HHMMSS}.json` | ⚠️ when `--format json/both` | structured data, containing `issues` / `issues_summary` / `effective_weights` / `reviewed_sheets` |

Reference output (Shenxin Zhimei 0820 manual, `--scenario full --process-sheet "Cutover Plan" --rollback-sheet "Rollback Plan"`): 44 key items to confirm (16 critical + 28 high), 0 items to note, overall score 12.5/100, risk level CRITICAL, appendix scoring dimensions being "Cutover Execution Steps 20 pts × 50% + Rollback Steps 5 pts × 50%".

On termination the Agent **must output to the user** (see "Final Answer Requirements (MUST)" for the mandatory opening summary line):
1. The absolute path of the report file (for direct opening)
2. The scenario actually used, as the literal CLI value (`full` / `batch` / `other`) and in words
3. The Sheet mapping actually reviewed, using the literal word `Sheet`, plus any extra review dimensions that were opened
4. The overall score and risk level
5. The number of CRITICAL-level issues
6. Next-step recommendations (remediation / rehearsal / review meeting)
7. Disclaimer: **"This report is generated based on rule matching, is for reference only, does not constitute the final decision basis, and please manually review the key items."**

> Note: this skill focuses on cutover-manual quality review. To configure Redis/ES/MySQL data migration tasks, use dedicated skills such as `redis-shake-migration` / `logstash-es-migration`.

## Applicable Scenarios

- Cutover-manual review for big-data stack migration and application cloud-migration projects
- Risk assessment before a cutover plan goes live
- Cutover Checklist completeness check
- Rollback plan feasibility verification
- Data migration plan completeness review

## Limitations

1. Only supports `.xlsx` format (does not support .xls / .csv / .pdf / .docx)
2. Requires structured headers, rows, and columns; unstructured documents cannot be scored
3. Review rules are designed in Chinese, with partial English keyword support
4. Does not deeply understand business logic; only does keyword and structure matching
5. **Desensitization in the report relies on manual review**; if the `--no-redact` mode is enabled to output the original text, the user must encrypt and store it themselves

## Additional Resources

- Installation, quick start, and command cheat sheet: [references/usage-guide.md](references/usage-guide.md)
- Scoring standard and scenario-specific review focus: [references/review-standard.md](references/review-standard.md)
- RAM permission declaration (zero permissions): [references/ram-policies.md](references/ram-policies.md)
- Version history: [references/changelog.md](references/changelog.md)
- Example cutover manual: [assets/example-cutover-manual.xlsx](assets/example-cutover-manual.xlsx)

---

*Last updated: 2026-08-24*
