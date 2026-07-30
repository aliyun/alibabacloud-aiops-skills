# Verification Method

Use the strongest applicable checks supported by the repository and confirmed local environment.

## Record evidence

Record one entry per check with scope, command or fixture, status, and supporting output. Use only these statuses:

- `passed`: the check ran and met its stated expectation;
- `failed`: the check ran and did not meet its expectation;
- `not run`: the check was inapplicable or blocked, with the reason recorded.

Keep local evidence separate from VVR-only checks. A missing tool, unavailable target, or unexecuted command is `not run`.

## 1. Static and repository checks

Run configured formatting, linting, type checks, and tests. Compile every changed Python file with `python -m py_compile <changed-python-file>`. Search changed job code for hardcoded credentials, unresolved placeholders, private APIs, and Table bridges not recorded in the documented path.

Complete this section when every configured applicable check has an evidence entry and each intentional exception has a reason.

## 2. Version and import checks

After the exact package version is confirmed, inspect or install that version in an isolated environment. Import every selected public symbol and match it to the exact versioned symbol page collected through [official-docs.md](official-docs.md).

Complete this section when the target VVR, local package, documentation version, and selected API surface agree, or each mismatch is reported. Label `ververica-flink` results as local API checks because target execution remains VVR-only.

## 3. Bounded behavior checks

Use finite fixtures for schema, expression, callback, dependency, and runtime-file behavior. Replace external connectors with bounded in-memory records when that preserves the behavior under test. Streaming-source checks use a bounded test path rather than an unbounded `collect`, `iter_rows`, or equivalent operation.

Complete this section when output schema, keys, null behavior, changelog expectations, and representative values match the target contract or each mismatch is recorded.

## 4. Deployment artifact checks

1. Confirm each applicable project-side script matches the selected project layout and syntax-check it with `bash -n`.
2. For modular code, run `scripts/package_code.sh` when safe, test and list the ZIP, and verify that Entry Module resolves at the archive root.
3. For non-pre-installed packages, apply [python-dependencies.md](python-dependencies.md). Run `scripts/build_dependencies.sh` when its Docker and compatibility conditions are met, then test and list `deps.zip`.
4. Compare the filesystem and README with [handoff-deliverables.md](handoff-deliverables.md) and [platform-runtime.md](platform-runtime.md). Verify every console-field mapping and reject raw `{{...}}` placeholders.
5. When code uses or mentions DataFrame LLM functions such as `llm.predict` or `llm.ai_*`, verify that the README points to Flink AI Service at `https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service`.

Complete this section when every selected artifact exists and passes its applicable check, or has a recorded blocker; every omitted conditional artifact has a reason; and the README matches the checked filesystem.

## 5. Target VVR checks

List checks that require the Alibaba Cloud workspace: connector reachability, attachment resolution, secret resolution, checkpoints, state restore, resource sizing, and production-like throughput. Give each check an owner, expected observation, and rollback or cleanup instruction.

Complete this section when every target-only assumption has a corresponding check and none is reported as locally passed.
