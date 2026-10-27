# Verification Method

## 1. Static Checks

From the repository root:

```bash
bash -n scripts/call_apsaradb_agent.sh
bash scripts/call_apsaradb_agent.sh --help
```

Expected results: shell syntax exits 0, and help lists every public option and describes readonly behavior. Validate the Skill version source as described in the `SKILL.md` Observability section.

## 2. Dependency and Credential Checks

Run `bash scripts/prepare_apsaradb_agent.sh` in an authorized setup step, then `bash scripts/prepare_apsaradb_agent.sh --check-only` before queries. The helper must prepare automatic plugin installation, update plugins, install missing DAS, and validate help. Unattended evaluations provision this before sessions start; no product plugin is needed for readonly agent requests.

If the platform exposes `ALIBABA_CLOUD_CLI_MOCK=true`, record that the run is simulated. Do not disable the platform mock or count the run as live-resource verification.

```bash
aliyun version
aliyun configure list
aliyun plugin list
aliyun das get-yao-chi-agent --help
jq --version
```

Confirm CLI 3.3.3 or later, a valid configured identity, the current DAS plugin, and `jq`. Never print credential values. Local utility and help commands do not receive a User-Agent.

## 3. Scoped Observability and Readonly Checks

Initialize `SKILL_SESSION_ID` and `SKILL_VERSION` as described in the `SKILL.md` Core Workflow, then run a dry-run:

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
  bash scripts/call_apsaradb_agent.sh \
  "test" --source yaochi-console --extra-info '{"lang":"en"}' --dry-run
```

Verify the request uses `POST /agent`, API version `2020-01-16`, action `GetYaoChiAgent`, and an `ExtraInfo` that contains `"mode":"readonly"` merged with the supplied fields. The CLI dry-run may omit transport headers from its display; check the exact UA product on the captured argument lists in the fake-stream verification below:

```text
AlibabaCloud-Agent-Skills/alibabacloud-apsaradb-agent/<fresh-session> skill-version/<skill-version>
```

Also verify missing, malformed, or mismatched `SKILL_SESSION_ID` and `SKILL_VERSION` fail before a cloud request.

## 4. Input Rejection

Run each command with valid generated scoped values. Each must exit nonzero before a cloud request:

```bash
bash scripts/call_apsaradb_agent.sh ""
bash scripts/call_apsaradb_agent.sh "test" --session-id invalid
bash scripts/call_apsaradb_agent.sh "test" --source unknown
bash scripts/call_apsaradb_agent.sh "test" --extra-info '[]'
bash scripts/call_apsaradb_agent.sh "test" --extra-info '{"mode":"write"}'
bash scripts/call_apsaradb_agent.sh "test" --extra-info '{"token":"placeholder"}'
bash scripts/call_apsaradb_agent.sh "test" --image-keys '{"bad":true}'
bash scripts/call_apsaradb_agent.sh "test" --confirm approve
bash scripts/call_apsaradb_agent.sh "connect with password=placeholder"
```

The test harness must inject `SKILL_SESSION_ID` and `SKILL_VERSION` into each command so failures reach the intended validator. Unknown options such as `--confirm` must be rejected as unknown. Secret rejection output must not repeat the supplied value, and the fake CLI log must show that no cloud request was attempted.

## 5. Fake-Stream Verification

Use a local fake `aliyun` executable that supports version, credential, plugin-help, and primary-stream behavior. Capture every argument without credentials and verify:

1. The request includes the expected versioned `--user-agent` and `--extra-info` with `mode` set to `readonly`.
2. A stream containing a `humanConfirm` UI call prints `[ReadonlyViolation]`, exits nonzero, and triggers no second `aliyun` cloud call.
3. A valid response followed by normal EOF succeeds only when the aliyun CLI exits 0; the same stream with a nonzero CLI exit fails.
4. An empty stream, malformed-only stream, or parser error remains a failure even when the CLI exits 0.
5. Empty, invalid, or unknown selected profiles stop before the cloud command even when `configure list` exits 0.
6. A transport error or nonzero CLI exit after response events remains a failure, prints `[IncompleteResponse]`, and preserves a valid returned SessionID exactly once for a related continuation. No automatic retry is made after partial output.
7. No credential or secret value appears in stdout, stderr, captured arguments, or artifacts, including under `--debug`.

## 6. Live Readonly Verification

Run only with user approval and an existing suitable identity, using the scoped values initialized from `SKILL.md`:

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
  bash scripts/call_apsaradb_agent.sh \
  "Explain what PolarDB is."
```

Verify exit 0, a complete stdout answer, a valid `[SessionID] <uuid>` on stderr, and a related follow-up using the same conversation SessionID and Skill observability values.

## 7. Readonly Scope Verification

Verify that resource creation, deletion, updates, and order execution are not advertised as supported capabilities. No local write-command fallback, product write permissions, or operation examples may be included. A mixed request may receive the requested readonly analysis, while the unsupported execution part is clearly identified. A service confirmation request remains a failure and is never approved.

## 8. Permission Error Verification

With an identity lacking the required action, verify a nonzero exit and a structured block containing code, message, available action, request ID, and suggestion. Then follow the RAM permission failure process in `SKILL.md`; do not automatically retry.

## 9. Setup Regression Tests

Run `python3 -m unittest discover -s tests -v`. The setup tests use an isolated CLI executable to verify install/update order, existing-plugin reuse, check-only, credential/version failures and fail-fast behavior, and make no cloud calls.

## 10. Business completion and evaluation interpretation

Verify the final answer states business findings and known gaps, not only artifact filenames. After a readonly plan is ready, duplicate or unfamiliar output files remain untouched without another cleanup question. Missing samples or unavailable service features must be identified without fabricated statistics or an unrequested feature activation.

Grade execution and business evidence semantically across the transcript and report files. Do not require literal Chinese keywords in an English answer, a slow-SQL duration when no slow SQL exists, or a fixed number of large keys when statistics are absent. Keep actual API failure distinct from these valid empty/unavailable results.

Report with-Skill and without-Skill groups separately. Script-specific assertions measure implementation adherence and are not a fair standalone business-quality measure for a baseline that has no bundled script. Preserve original scores alongside any semantic review; changing case files does not change historical run results.

## 11. Concurrent-limit recovery

Use the isolated CLI and fake sleep in `tests/test_agent_stream.py` to verify: an explicit `Throttling.UserConcurrentLimit` before any response can recover; replayed arguments are identical; retry count and jittered delays are bounded; exhausted retries remain failures. A partial response, returned SessionID, permission error, generic transport failure, or write-confirmation request must not be retried. Invalid retry budgets fail before a cloud call. This recovery does not guarantee shared-account admission or bypass the service concurrency limit.
