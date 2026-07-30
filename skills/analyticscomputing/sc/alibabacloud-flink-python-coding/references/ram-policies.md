# RAM Policies

## Core workflow

The coding-only workflow calls no Alibaba Cloud API and requires no RAM action. Local source inspection, editing, linting, compilation, and bounded tests require no Alibaba Cloud credential.

## Separately authorized operations

File upload, deployment creation or start/stop, workspace inspection, configuration changes, and target connector access are operational expansions. For each separately requested operation, identify the exact console action or API, resolve its current permission documentation, and confirm its parameters before execution. A product name alone is insufficient evidence for a RAM action.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Completion criterion

Complete permission analysis when every separately authorized operation has direct permission evidence, or execution is paused at the required permission gate.
