# Pre-Clarification Script

Business facts to clarify in Step 0. **Binding parameters are internal skill implementation details, the user does not need to understand the configuration**; but this time we need to ask the user for two resource names (SLS Project and CMS 2.0 workspace), because they are the only clues to where the data resides.

> **[MUST] Clarification script**: If the same environment binding already exists in conversation history, reuse it directly — do not ask again. When not available, ask for the following five items,
> **do not send help documentation links to the user**.

"To locate your Agent trace data, I need five pieces of information:

① **Agent application name** — Log in to the **Cloud Monitor 2.0 console**, on the left side **AI Agent Observability**, under the top **AI Agent** tab, the **AI Applications** sub-tab — just give me the verbatim text from the **Application Name** column in the list.

② **Region** — Which region is your Agent application deployed in (e.g., 'China East 1 (Hangzhou)'); you can see it in the region selector at the top right of the console.

③ **Time range of the trace** — Which day, which time period (**the more precise the better, maximum 4 hours**), for example 'August 28, 14:00–17:00'.

④ **Where the data is stored** (provide **at least one of the two**, both preferred):
- **SLS Project name** — eBPF-collected runtime facts (process/network/HTTP) are stored here, its `ebpf-event`
  logstore is this skill's eBPF data source.
- **CMS 2.0 workspace name** — LoongSuit-collected native traces and framework state are stored here,
  this is this skill's LoongSuit data source.

⑤ **Which trace to analyze (trace_id)** — The trace ID you obtained from application logs, the trace console, or alerts;
one analysis corresponds to one trace."

## Follow-Up Points for Each Item

### ① Application Name (`--service-name`)
- **Copy verbatim**: This is an exact match — wrong case or suffix will cause the LoongSuit side to return 0 rows — that's not a connectivity gap, it's a wrong name.
- This parameter **only takes effect on the LoongSuit side**: ebpf-event index has no `service.name`, so eBPF side always marks
  `service_filter_unavailable`. To narrow eBPF side, use `--agent-type` / `--comm` / `--container-id`.
- Only omit when genuinely doing cross-application horizontal comparison, and note in the report that narrowing was not applied.

### ② Region (`--region`)
- Both data sources are region-level resources, same environment means same region on both sides.
- Required, no script can run without it.

### ③ Time Range (`--from/--to`)
- **Guide the user**, do not accept vague answers like "last week" or "a few days ago": first ask **which day** (offer candidate dates if necessary) → then narrow to
  **which hours** (morning/afternoon/around what time) → finally **propose a specific candidate slice for user confirmation** (e.g., "So I'll query August 28
  14:00–17:00, that 3-hour window?").
- When the user only remembers "roughly afternoon", propose a ≤4h slice for confirmation, **do not expand the span to the whole day**; if longer coverage is genuinely needed,
  **split into multiple ≤4h slices and query each**.
- When converting to unix seconds, **must include `:%S`**, otherwise `date` will fill in the current seconds and the span will be imprecise:
  ```bash
  # macOS
  date -j -f "%Y-%m-%d %H:%M:%S" "2026-08-19 22:00:00" +%s
  # Linux
  date -d "2026-08-19 22:00:00" +%s
  ```
- When span > `AGENT_OBS_MAX_WINDOW_HOURS` (default 4h), **do not execute any query scripts** — the script won't stop you, it will just be extremely slow.

### ④ Two Resource Names (`--project` / `--workspace`)
- **Providing at least one is sufficient to run**: only `--project` → execution automatically narrows to eBPF side; only `--workspace` → narrows to
  LoongSuit side. The absent side will be marked as a **connectivity gap** in the output (`sources.<name>.bound=false` + `gap`),
  not silently degraded.
- **Always use the verbatim text from the console/API**, do not guess by name, do not concatenate. Auto-created resources look like
  `agentloop-<32-char-code>` / `default-cms-<uid>-<region>`; when using an existing workspace, it's the user's own name.

### ⑤ Target Trace trace_id (`--trace-id`)
- **This skill only does trace analysis, one trace at a time**: the analysis unit is the user-specified trace_id, the skill does not
  sample "which trace is most worth viewing", nor does it do per-trace summary ranking.
- When the user cannot provide a trace_id: **first run `trace_overview.py` to get `trace_candidates`**, present each candidate's `input_summary` (the user's original query excerpt) so the user can identify the target trace by its content rather than by opaque hex ID — whichever the user picks is the one to use; the skill does not select on behalf, does not sort or recommend "the most important one".
- When the user-provided trace_id is not found in the slice: **shift the slice** (move `--from/--to` to the time period when the trace actually occurred, span unchanged)
  and try again, **do not enlarge the span**; you can also ask the user to verify the ID is copied correctly (32-character hex).
- When the user says "help me see which trace has problems" — this kind of **sampling request**: explain that the skill does not make sampling judgments, present `trace_candidates` (with `input_summary` showing each trace's original query)
  or `by_operation`/`by_tool` window facts to help the user choose.

## What to Do When the User Cannot Provide the Information

The skill **has no auto-discovery mechanism**. When the user cannot provide these two names:

- **State honestly that you cannot continue**, do not guess, do not concatenate resource names based on naming patterns (auto-created resources look like
  `agentloop-<32-char-code>` / `default-cms-<uid>-<region>`, concatenated names are almost certainly wrong,
  wrong names cause queries to silently return 0 rows, which is then misjudged as "no data in the window").
- **Explain the console navigation path in text** (do not send documentation links):
  - **CMS 2.0 workspace name**: Log in to the **Cloud Monitor 2.0 console**, the name in the workspace list.
  - **SLS Project name**: Log in to the **Log Service console**, the name in the project list (the one that stores the `ebpf-event`
    logstore).
- Have the user read it to you verbatim, and let the **Agent itself** fill it into each command, **do not ask the user to export or write it into environment variables**.
- Getting only one name is still runnable (automatically narrows to that source), the absent side is marked as a connectivity gap.

## Run Preflight Immediately After Clarification

After obtaining bindings and before issuing any queries:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/preflight.py --region <region> \
  --project <SLS Project> --workspace <CMS workspace>
```

Details of the seven checks are in the preflight checks reference. The unbound side will be `skipped`, which is a valid configuration.

## Clarification Record (Sole Execution Prerequisite)

Before entering any query, you must explicitly leave a conclusion line in the conversation:

> Application name = {service-name}; Region = {region}; Binding project={project} / workspace={workspace}
> (provided by user); Target trace trace_id = {trace-id} (user-specified); Maximum window limit = {N}h (span cap);
> Confirmed slice with user = {YYYY-MM-DD HH:MM}~{HH:MM} (`--from {ts} --to {ts}`), span {X}h ≤ {N}h;
> Proceeding with Step {n}.

**Do not issue any query without this record.**

## Things Not to Ask the User

- `--agent` (`gen_ai.agent.name`): Not present in any console list. Run the script first, enumerate actual agent names from the output,
  then let the user choose.
- Environment variables: Bindings only go through CLI arguments, scripts do not read any binding-type environment variables.
- Help documentation links: Do not send documentation to the user during clarification, ask for business facts directly.
- AK/SK/STS token: Never request, echo, print, or dump under any circumstances. Forbidden commands include `echo $ALIBABA_CLOUD_*`, `env | grep -i access/secret/token`, `printenv`, `cat ~/.aliyun/config.json`, `cat ~/.alibabacloud/credentials` — all expose credential values in the terminal transcript. Credential status is checked only via `aliyun configure list` (which masks values, showing only the type prefix).
