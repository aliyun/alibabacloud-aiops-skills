# Agent readiness and the decision tree

The full reasoning chain behind `triage`, written out so a human (or the
`explain` mode) can walk it without re-deriving anything. Facts below come from
the case history of this scenario; where a case did not close, the entry says so, and
confidence drops accordingly.

## The tree

```
0  Inputs: instance id + the region named by the console error.
   Missing either -> ask. Never guess a region.
1  Ownership gate: DescribeInstances in that region, for that id.
   Not visible -> stop: "wrong region or different account" (case T-D87E8F47
   died exactly here; account tail from check-env is printed for comparison).
2  Lifecycle gate: DescribeInstanceStatus.
   Not Running (Pending/Starting/Stopping/Stopped) -> the agent verdict is
   unreliable -> hand off to the instance-state area with this report attached.
3  History: DescribeInvocations for the instance (newest first, optional
   --hours window, optional --invocation-id).
   - No records at all  -> readiness branch (below): missing / stopped /
     blocked agent, or empty requested window. Features that failed with a
     Cloud Assistant error (rows 6-7 of error-signatures) land here too.
   - Timeout wording    -> COMMAND_TIMEOUT: candidates = saturation, guest
     volume full / inodes exhausted, agent absent, script over its own
     timeout.
   - CLIENT_RESTARTED / interrupted without exit code -> CLIENT_RESTARTED:
     load-side evidence list; the source case did not close - do not promise
     more than it earned.
   - OS-level error strings on every command (Windows image/resource-type,
     "internal or external command") -> GUEST_ENV_BROKEN: channel works,
     guest broken -> hand off (instance-state / OS repair), snapshot first.
   - Installer/package text in Output, channel healthy -> SOFTWARE_INSTALL_
     FAILED: compatibility guidance, manual.
   - Command content is an expansion task -> EXPAND_TASK_FAILED: classify the
     failure (load / missing tool / resolver / Windows not covered), then
     hand the growth to disk-expand.
4  Environment exclusion (consent, one command at a time): df_h, then df_i on
   Linux (or get_volume on Windows, with the MFT-confidence caveat) - full
   table in guest-commands.md. This replaces the ticket ritual of "run these
   three commands and send screenshots" (cases T-99046C78, T-79753A0F): the
   customer confirms instead of typing.
5  Abuse recognition at any point: history lines the customer denies issuing
   -> switch to the evidence flow (below) and stop treating it as a fault.
6  Report: conclusion + confidence, evidence lines each tagged (cloud query /
   consented guest command / history record / customer-side step), commands
   executed vs refused, uncertainties, next step. Any cleanup/repair advice
   that touches state -> snapshot first (consented).
*  Any leg unavailable (channel down because it IS the subject, permission
   denied, customer declined) -> STATUS: DEGRADED + the reading list the
   customer pastes back (guest-commands.md, "Degraded mode"). Case T-FA7FC9EE
   proves declining instance operations is a real workflow, so this exit is a
   first-class branch, not an error.
```

## Readiness: agent missing / stopped / offline / outdated

What the agent is, in customer language: the in-instance service that lets the
console and API run commands, and that also carries password-free Workbench
login, online password reset and ECS file backup. When those features "suddenly"
break, the shared cause is usually this service (case T-BB00A07B opened with
exactly that surprise).

Customer-side steps, printed verbatim, never executed by the skill (service
control is outside the guest whitelist under the command safety policy - the
`systemctl` prohibition):

**Linux**
1. Check state: `sudo systemctl status aliyun.service` (customer-run).
2. Start it: `sudo systemctl start aliyun.service` (customer-run).
3. Missing or too old: install or upgrade per the official agent-installation
   page (link below); note the supported-OS list - images without the agent, or
   OS versions outside auto-install, explain a never-present agent
   (case T-672E1C69).
4. Verify: re-run `triage`; a new successful history line is the proof, not the
   customer's feeling that it "looks started".

**Windows**
1. Open the services manager; read status and startup type of
   "Aliyun Assist Service" (customer-run).
2. Start it there if stopped.
3. Install/upgrade via the same official page.
4. Verify the same way as Linux.

Version-too-low is a distinct, verified root cause in this scenario (case
T-1A68E453: the support engineer read the agent's own log, found the service
endpoint unreachable, and concluded "version too low - upgrade"). The log read
itself is outside this skill's whitelist, so the offer is: upgrade first, or
have the customer paste the log lines around the failure time.

System-disk re-initialisation (ReplaceSystemDisk / re-init) is associated with
an agent that never comes back online (case T-270E4605, 57 consecutive empty
health checks - closed without a verified cause; confidence low, test the
reinstall path). The re-init page is linked below; treat the association as a
question to ask, not a finding to state.

## Features blocked by the agent, and their fallbacks

| Feature | Dependency | Fallback while the agent is down | Docs |
| --- | --- | --- | --- |
| Online password reset | running agent, sufficient version | Offline reset: reboots the instance, expect business interruption; snapshot first (the source thread disclosed exactly this order) | instance-logon-credential-management, reset-the-logon-password-of-an-instance |
| ECS file backup (Essential Edition) | running agent | Fix the agent, re-run the backup; there is no agent-free path | install page + workbench-overview (feature context) |
| Workbench password-free login | agent to install the temporary key | Password or key-pair login directly | workbench-password-free-login-principle-temporary-ssh-key-pair |

## Suspected abuse: the evidence flow (recognition, then hand off)

What this skill produces: the execution-history evidence list
(`invocations --region-id ... [--instance-id ...] --include-output`) -
timestamps, instances, command names, exit codes, retained output. That is the
checklist version of what the source cases asked for by hand ("look up which
commands were actually executed" - T-9BEAB951; "is this process yours, if not
we will kill it" - T-2A028B99).

Then, in order, all manual:
1. Disable the leaked access key and rotate credentials (RAM console - this
   skill never reads or governs keys).
2. Snapshot affected disks before anything is touched (`snapshot-guard`,
   consented).
3. Persistence removal - processes, cron entries, files, scheduled tasks -
   belongs to the security responder (in T-2A028B99 that happened over an
   authorised VNC session after rollback revealed survivors).
4. New key with least privilege and network access conditions; close the
   exposed service port that let the intruder in.
5. Recommend enabling automatic saving of command results (link below) so the
   next intrusion leaves full on-instance evidence.

Boundary: this scenario never kills, deletes, disables or restricts - evidence and
guidance only. No official AK-leak runbook URL was verified for this scenario; the
console paths are the guidance.

## Documentation used by this skill

Only the pages below are cited anywhere in the package; they were each either a
search hit for this scenario or a link actually sent in a source ticket.

| Topic | URL |
| --- | --- |
| Install / upgrade the agent | https://help.aliyun.com/zh/ecs/user-guide/install-the-cloud-assistant-agent |
| Workbench script library (manage assistant commands) | https://help.aliyun.com/zh/ecs/user-guide/workbench-script-library.md |
| Automatic saving for Cloud Assistant command output | https://help.aliyun.com/zh/ecs/user-guide/enable-automatic-saving-for-cloud-assistant-commands-on-instances.md |
| Create a Cloud Assistant command | https://help.aliyun.com/zh/ecs/user-guide/create-a-command.md |
| Run an existing command | https://help.aliyun.com/zh/ecs/user-guide/run-a-command.md |
| Query commands (API reference for the console list) | https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-describecommands.md |
| Workbench overview | https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md |
| Workbench password-free login principle | https://help.aliyun.com/zh/ecs/user-guide/workbench-password-free-login-principle-temporary-ssh-key-pair.md |
| Workbench CLI manages instances | https://help.aliyun.com/zh/ecs/user-guide/use-workbench-cli-to-manage-ecs-instances.md |
| Workbench AI agent mode | https://help.aliyun.com/zh/ecs/user-guide/workbench-ai-agent-mode.md |
| Instance logon credential management | https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management.md |
| Offline password reset | https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance |
| Re-initialize a system disk | https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk |
| Detach or attach a system disk (offline repair path) | https://help.aliyun.com/zh/ecs/user-guide/detach-or-attach-a-system-disk.md |
| Create a snapshot | https://help.aliyun.com/document_detail/25455.html |
| Snapshot billing | https://help.aliyun.com/document_detail/56159.html |
| Delete a snapshot | https://help.aliyun.com/document_detail/128131.html |
| Expand a Linux partition and filesystem (hand-off ref) | https://help.aliyun.com/document_detail/25451.htm |
| Windows disk expansion (hand-off ref) | https://help.aliyun.com/zh/ecs/user-guide/resize-windows-cloud-disks.md |
| Linux data-disk offline extension (hand-off ref) | https://help.aliyun.com/zh/ecs/user-guide/offline-extend-partitions-and-file-systems-on-a-data-disk-of-a-linux-instance.md |

## Verified gaps (state them; do not fill them from memory)

- No verified live agent-status query for this scenario (the status API was not in
  the verified surface): readiness is history plus wording, and the report says
  "no live status was read" wherever it matters.
- No verified CloudMonitor query: saturation hypotheses must be confirmed by
  the customer in the console (the source cases read it from support-side
  tooling this skill does not have).
- No verified official troubleshooting guide URL specifically for agent-status
  handling; do not invent one - the install page plus this tree are the path.
- The second member scenario of this product area was not delivered in evidence;
  this package covers the command-failure / offline-agent area only.
- atop installation and the AK-leak runbook: named as documents, no URLs,
  because none was verified.
