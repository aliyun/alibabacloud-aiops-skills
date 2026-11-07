# Evaluation fixture contract

Maintainer reference for the sandbox-only extensions used by `evals/`.
Start with [parallel evaluation](evaluation.md) for ownership, cleanup and gates.
Production scripts use the normal credential chain and have no mock mode.

`mocks` and `mock_action` are platform extensions, absent from the published
scenario schema. Native CLI records require `name`, `cmd`, `exit_code`, `stdout`,
`stderr`, and `times`; `id` is not a supported substitute for `name`. Command
patterns include the product, for example `eiam list-instances *`, because matching
uses arguments after `aliyun`. See the vendor's [record schema](https://github.com/aliyun/aliyun-cli/blob/46ce07bfeb2db04d1505ccc0dcf584479da95267/sysconfig/mock/types.go)
and [command matcher](https://github.com/aliyun/aliyun-cli/blob/46ce07bfeb2db04d1505ccc0dcf584479da95267/sysconfig/mock/matcher.go).
Error fixtures include the vendor v1 envelope recovery object; successful POP
responses do not claim the error-envelope schema version. See the vendor
[error envelope](https://github.com/aliyun/aliyun-cli/blob/46ce07bfeb2db04d1505ccc0dcf584479da95267/cli/agent_error.go).
One malformed record blocks loading the whole store. Matching is case-sensitive;
fault scenarios use plugin-mode lowercase, hyphenated commands and flags.

The four `error_type` values are `permission`, `parameter`, `throttling`, and
`internal`. Native import/consumption tests validate every fixture in isolated
stores with a final catch-all failure to prevent real-cloud fallback. These tests
do not establish the platform's `mock_action` reference contract: parsing,
injection and grading still require platform run evidence. Source fixtures retain the platform-generated fields `id`, `name`, `cmd`,
`exit_code`, `stdout`, `stderr` and `times`. Their names equal their IDs so both
platform references and the native CLI store use the same identity. Platform-generated cases use `mock_id`, `action_after_error` and `match_type` for error expectations. Use `mock_id` to reference the source fixture ID; the former `mockId` and `ref` spellings did not identify the target. The four write-fault cases request a remediation decision and obey the scripted stop response, matching `action_after_error: ["hitl"]` without replaying writes. A testcase-guarded setup hook, configured in
`evals/config/resource-scripts.json`, runs after injection and before the agent.
It validates the store, rejects conflicting IDs or unknown fields, and atomically
writes only native CLI fields with mode 0600, translating `id` into `name` and
defaulting `stderr` to an empty string. Thus `id` remains in the testcase
for platform analysis, but is removed from the runtime CLI store whose strict
loader rejects it. The hook requires `TESTCASE_UUID` to prevent accidental use
against a developer's normal CLI configuration. The business scripts do not
perform this conversion or implement a mock mode.

Negative CreateApplication calls are expected to return a non-2xx fault. Score
their exact invocation through the parameter-constrained fixture and `mock_action`; do not require a successful API invocation for the
same intentionally failing call. Keep successful discovery calls as independent
API assertions. The setup hook adds a local rejection record for unexpected
CreateApplication parameters in these four cases, preventing a changed SSO type
from falling through to the real cloud. Help does not contain an instance ID and
cannot consume the parameter-constrained fault. This guard exists only in the
evaluation sandbox and does not alter production execution.

The ECS permission fallback must retain exit code 2, `NO_PERMISSION`, the
actual `Forbidden.RAM` and fixture RequestId in both execution evidence and the
final report. A real disabled PAM state cannot substitute for the injected
`pam-disabled` branch: direct evidence must also contain its fixture RequestId.

HITL fixtures use concrete static signature/scope values because the observed
platform reply path forwarded `${params.*}` literally. Resource IDs always come
from that same case's actual query or creation response. Never embed injected
error codes or RequestIds in the prompt: diagnosis must come from the response.
