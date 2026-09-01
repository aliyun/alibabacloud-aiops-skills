# RAM Permissions

GuestOS-level diagnostics (both online and offline, direct execution channel) run PowerShell inside the instance and require **no RAM permissions**. RAM permissions are required **only for the remote execution channel**, where the Alibaba Cloud CLI calls ECS Cloud Assistant APIs from the machine running the agent.

## required_permissions

`ecs:RunCommand` -- Send PowerShell diagnostic/fix scripts to the target instance via Cloud Assistant (remote execution channel; the only write-capable action in this list)

`ecs:DescribeInvocationResults` -- Poll command execution status and retrieve the Base64-encoded output

`ecs:DescribeInvocations` -- List past command invocations for the instance (audit and history; optional)

`ecs:DescribeInstances` -- Verify target instance existence, Running state, and OSType before entering the remote channel

`ecs:DescribeRegions` -- Enumerate region IDs when the region of the target instance is unknown

`ecs:DescribeInstanceMonitorData` -- Fetch instance CPU and network BPS/PPS monitoring data as auxiliary cross-validation evidence in online diagnosis (remote execution channel; optional)

`ecs:DescribeDiskMonitorData` -- Fetch per-disk IOPS/BPS/latency monitoring data as auxiliary cross-validation evidence in online diagnosis (remote execution channel; optional)

`ecs:DescribeInstanceHistoryEvents` -- Query system event history (maintenance / migration / host error events) for fault-time correlation in online diagnosis (optional)

`ecs:GetInstanceScreenshot` -- Retrieve the console screenshot (Base64 JPEG) for screen-state cross-validation in online diagnosis (optional)

`ecs:DescribeSecurityGroupAttribute` -- Read security-group ingress/egress rules for platform-side triage of "unreachable from outside" and "public unreachable" symptoms (remote execution channel; optional, read-only)

`ecs:DescribeDisks` -- Read cloud-disk metadata (status, category, size, attachment) for platform-side triage in online diagnosis and disk-scoped evidence in offline diagnosis (remote execution channel; optional, read-only)

`ecs:DescribeInstanceTypes` -- Query instance-family NVMe protocol support (`NvmeSupport`) for the NVMe applicability gate before stornvme diagnosis (remote execution channel; optional, read-only)

`ecs:DescribeImages` -- Query whether the image contains the NVMe driver (`Features.NvmeSupport`) for the NVMe applicability gate before stornvme diagnosis (remote execution channel; optional, read-only)

## Notes

- The action identifiers above (`ecs:RunCommand`, `ecs:DescribeInstances`, ...) are **RAM policy actions** and use the PascalCase API names. This is a different namespace from the aliyun CLI plugin-mode subcommands and flags (`aliyun ecs run-command`, `--biz-region-id`): in a RAM policy JSON the `Action` element only matches the PascalCase API names, so these identifiers must NOT be converted to kebab-case -- a policy declaring `ecs:run-command` matches no action and grants nothing.
- Permissions are declared per-action with no wildcards; grant exactly the actions above rather than a broad system policy.
- All actions are read-only except `ecs:RunCommand`, which delivers scripts that execute as SYSTEM on the target instance. Fix scripts additionally require explicit user confirmation before being sent (SKILL.md Principle 6).

## Authorization Flow on AccessDenied

When any remote-channel CLI call returns `AccessDenied` / `Forbidden.RAM` (non-zero exit with that error code in stderr), the caller's identity lacks the RAM Action for that API. Permission state is owned by the user -- the agent can neither grant itself permission nor infer that the problem resolved itself. The flow below is mandatory; it applies identically to the prerequisite gate calls (e.g. `describe-instances`) and to later calls (`run-command`, polling, monitor-data).

1. **Stop immediately -- no blind retry.** Retrying the same call with the same identity cannot grant permission. This holds even if a retry happens to succeed (e.g., eventual-consistency window after a recent grant the user never mentioned): a stray success does not close the incident. Continuing the diagnosis as if nothing happened hides a real authorization gap from the user, and the next API call can fail again mid-flow. Observed anti-patterns to avoid: error -> read this file -> re-run the same command -> proceed with the full workflow; error -> read this file -> probe a different API to see whether IT is authorized (even framed as a "connectivity test" or "permission check") -> proceed with the full workflow through that API. Both variants skip the only step that can resolve the incident: telling the user.
2. **Report to the user and request the grant (HITL)**. State: the failed API call, the exact missing Action from the required_permissions list above (e.g. `ecs:DescribeInstances`), and how to grant it (add the Action to the RAM user/role policy the CLI is configured with). Do not handle, print, or ask for credentials -- the grant happens in the user's RAM console or policy tooling, outside this conversation.
3. **END the turn.** Do not enter any WORKFLOW-GUIDE, do not send any `RunCommand` or any other cloud API call, and do not fall back to another channel while the authorization question is open. The fact that the user already supplied the instance ID or asked for a fix does not authorize bypassing the gate: identity information and RAM permission are separate prerequisites, and having one never substitutes for the other.
4. **Resume only on explicit confirmation.** After the user confirms the grant in a later message, retry the failed call once. If it is still denied, report the continued failure with the exact error and stop -- no further retries, no silent workaround.
