# Scripts - safe_aliyun & safe_mutate

This skill unifies the "retry / single-step confirmed submission" semantics of all mutating CLIs through bash wrappers.

---

## `safe_aliyun` - retry wrapper

### Semantics

```
safe_aliyun aliyun <namespace> <action> [args...]
```

The first argument is fixed to `aliyun`; the wrapper is responsible for:

1. Auto-injecting `--insecure` for the test region `cn-wulanchabu-test-6`
2. Auto-injecting the Observability `--user-agent` (session-level UA from `LJ_USER_AGENT`, see SKILL.md Sec.Observability)
3. Whitelist errors (5xx / `Throttling*` / network timeout / TLS / DNS / EOF) -> exponential backoff `2s/4s/8s` + jitter, at most 3 times
4. Throttling `Throttling*` / HTTP 429 -> fixed 60s wait, at most 3 times
5. Blacklist errors (auth / authz / business 4xx / task terminal failure) -> return immediately, no retry
6. Every retry logs to stderr: `retry #N after <err> sleeping <s>s`

### Loading contract

Before the **first** `aliyun` call of each session, the following must be executed:

```bash
source "$LJ_SKILL_DIR/lib/lj_init.sh"
```

Any `aliyun *` issued before the type self-check passes counts as a V1 self-violation.

---

## `safe_mutate_oneshot` - single-step confirmed submission

### User-facing flow (sole entry point)

1. The Agent presents, in **one single message**: the parameter confirmation table (with a danger notice on top for F3/F4) + the closing prompt (zh sessions use the canonical prompt from `lib/core/i18n.sh` key `render.confirm_prompt`; en sessions "Please review the parameters above and reply 'confirm' to execute"). **No** cloud API is called at this point.
2. The user replies the confirmation word (zh sessions per `render.confirm_word`; en sessions `confirm`, case-insensitive; the other language's word is not accepted) -> the Agent executes:

```bash
safe_mutate_oneshot <tag> --intent "<user's original utterance>" aliyun eflo-controller <action> [args...]
```

3. Any other reply (cancel / a new question / a vague answer) -> no submission; emit a [paused] Not Executed report. If the user asks to change a parameter, regenerate the confirmation table and ask again (still the same step).

### Internal mechanics (transparent to the user)

`safe_mutate_oneshot` internally performs: parameter freezing (base64 dump to `/tmp/lingjun-mutate/`) -> hash verification -> assembly into `safe_aliyun aliyun ...` submission -> dump cleanup. This guarantees "the parameters the user confirmed = the parameters actually submitted".

> [WARN] Internal terms such as hash / token / Phase 1 / Phase 2 / `safe_mutate_confirm` must never appear in user-facing output; never ask the user to type any command or phrase verbatim - the confirmation word is language-matched (zh / en per `lib/core/i18n.sh` `render.confirm_word`).

### Risky-operation notice (F3 / F4)

Confirmation messages for `reimage-nodes` (data wipe) and `renew-instance` (paid) **must** open with a danger notice box (per-node detail / cost estimate), but the confirmation method is unchanged: reply the language-matched confirmation word in the same screen; no extra phrases needed.

### Low-level functions (script/test orchestration only, never user-facing)

`safe_mutate <tag> [--intent ...] aliyun ...` (freeze parameters, emit hash) and `safe_mutate_confirm <hash>` (replay submission) remain in `mutate-runner.sh` for the test suite (`MUTATE_AUTOCONFIRM=1`) and scripted orchestration; interactive sessions always use `safe_mutate_oneshot`.

---

## Implementation locations

- `lib/lj_init.sh` (one-stop bootstrap entry; also exports Observability session-id / UA)
- `lib/core/i18n.sh` (zh/en bilingual layer, incl. `render.*` / `pname.*` / `state.*` canonical zh strings)
- `lib/core/aliyun-call.sh` (safe_aliyun retry + audit + UA injection)
- `lib/core/aliyun-guard.sh` (whitelist gate + Region lock)
- `lib/core/mutate-runner.sh` (safe_mutate / safe_mutate_oneshot)
- `lib/core/task-poll.sh` (poll_task async task polling; the statutory polling method for interactive sessions - see polling interaction contract below)
- `lib/query/query.sh` (unified query entry, 11 subcommands)
- `tests/helpers/test-helpers.sh` (init_report / record_case / assert_*)
- `tests/helpers/bootstrap-inline.sh` (discovered.json fixture, TTL 1800s)
- `tests/helpers/feature-test-init.sh` (common test entry template)

Tests are loaded uniformly by `tests/00-bootstrap.sh`; feature test scripts use `tests/helpers/feature-test-init.sh`.

---

## Async task progress interaction contract (MANDATORY in interactive sessions)

1. **Submission receipt first**: the moment the submit returns, echo in the **visible reply body**: action + `TaskId`|`InvokeId`|`OrderId` + `RequestId` + ETA (Markdown table; zh sessions use the canonical zh labels from `lib/core/i18n.sh` `render.receipt_action` / `render.receipt_eta`). Writing it only in thinking is invisible to the user and **counts as no report** = V7 violation.
2. **Default: on-demand checks, no continuous polling.** After the receipt, end the turn with the estimated completion time + the on-demand progress prompt (zh per `render.progress_ondemand`; en: "reply 'check progress' anytime and I will query and report immediately"). When the user asks for progress, run a single `describe-task` (F7: `describe-invocations`) and produce a full status report in the body: TaskState + elapsed time + current Steps/sub-task phase + task ID; on terminal state run the verification (describe-node etc.) and write the final report in the body. Rationale: continuous real-time progress inside chat is structurally impossible in this IDE (mid-chain narration folds into thinking; per-round commands trip loop protection; the collapsed terminal block shows only the command echo).
3. **Optional: terminal watch mode - only when the user explicitly asks to watch/monitor continuously**:

```bash
bash "$HOME/.qoder/skills/alibabacloud-lingjun-node-ops/lib/lj_poll.sh" me-east-1 <TaskId> "Node Reimage"   # default cap=1200s, 10s/round
bash "$HOME/.qoder/skills/alibabacloud-lingjun-node-ops/lib/lj_poll.sh" me-east-1 <TaskId> "Node Stop" 900 10
```

(The operation label argument is rendered via the i18n layer; zh sessions pass the canonical zh feature name from `render.feat.*`.)

The launcher self-bootstraps (never prepend a long export/source chain); the startup banner prints immediately, then one heartbeat line per ~10s. The reply must state that the live stream is in the expanded terminal block / bottom terminal panel; during polling the Agent periodically (~ every 60s) snapshots the terminal and relays the latest heartbeat; after a soft timeout (rc=2) report in the body + HITL two-way pick.
4. **Forbidden in any mode**: splitting rounds into separate Bash calls (trips loop protection); silent backgrounding; `LJ_QUIET=1` in interactive sessions; fabricating progress lines without a real API response.
