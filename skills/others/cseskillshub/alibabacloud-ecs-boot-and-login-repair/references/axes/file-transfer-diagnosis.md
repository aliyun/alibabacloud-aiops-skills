---
name: alibabacloud-ecs-file-transfer-diagnosis

description: |
  Diagnoses ECS file transfers that fail, stall or hit a size limit, then returns an evidence report and the next step. Use when: cannot upload file to ECS; download very slow or stalls; FTP or SFTP transfer fails; console has no upload entry; uploads report Permission denied; ECONNREFUSED; errno 110; large file size limit. Do NOT use for: SSH or RDP connection faults, account lockout or credential recovery, cross-border packet loss, bandwidth changes or billing, disk space or inode exhaustion, disk expansion, instance start and stop, Web Hosting FTP, or Wuying Cloud Desktop.
---

# ECS file transfer diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Handles one symptom area: a file moving between a customer workstation and an
ECS instance (or between an instance, another instance, object storage and the
console) that fails, is refused, is too slow, or lands somewhere unexpected.
The scripts gather what the cloud can prove, the references decide what it
means, and the answer always ends with a next action.

## What this skill may and may not do

This skill is not query-only. It has exactly two kinds of capability.

1. **Cloud queries** through the bundled scripts: `ecs:DescribeInstances`,
   `ecs:DescribeInstancesFullStatus`, `ecs:DescribeCloudAssistantStatus`,
   `ecs:DescribeInvocations`, plus `sts:GetCallerIdentity` for the identity
   preflight. These change nothing and need no confirmation.
2. **One gated command channel**: `ecs:run-command`, used *only* to send a
   single non-mutating inspection command from the whitelist in
   `references/file-transfer-diagnosis__customer-commands.md`, and only after the confirmation gate
   below.

**ABSOLUTE PROHIBITION.** Never call, never generate, and never recommend that
the customer run on your behalf any action outside that list. In particular
there are no security group rule edits, no credential or key changes, no
instance lifecycle operations, no disk or snapshot operations, no bandwidth
changes, and no permission or ownership changes (`chmod`, `chown`) inside the
instance. There is no file removal, no formatting and no service restart in
this skill. Anything of that kind is handed to the customer as a written step
with its risk stated, never executed by the agent.

### Confirmation gate for in-guest commands (mandatory)

Before **any** call to `ecs:run-command`, the agent MUST, in this order:

1. State the exact command line that will run, character for character.
2. State the scope: this one instance, this one command.
3. State the effect: the command inspects state and changes nothing, so no
   rollback is required.
4. Ask for approval, and treat an approval as valid for that single command
   only. A second command requires a second approval.

`scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py guest-plan` implements this gate: with
no `--confirm` it prints the gate text and stops. Only add `--confirm` after
the customer has approved that exact command. The script rejects any command
outside the whitelist and prints it instead as a step for the customer to run
and paste back; that rejection is final, so do not retry the same command
through another route.

Default to customer-run output. Most of what identifies a transfer fault lives
in the instance and on the customer's own network, and the established pattern
is: give the command, the customer runs it, the customer pastes the output.
Commands such as `iftop`, `ss`, `netstat`, `iptables`, `firewall-cmd`, panel
helpers such as `bt`, and every `sysctl -w` change are outside the whitelist
and stay in that manual lane (`references/file-transfer-diagnosis__customer-commands.md`). A `sysctl`
change must additionally be stated as temporary until the next restart.

**Overseas regions.** For instances outside mainland China (for example the
United States regions), remote assistance on the instance is restricted by
policy and even human support cannot operate them remotely. Announce this, then
work from customer-pasted output; do not attempt the guest channel there.

### Windows instances

The whitelist covers Linux commands only. For a Windows instance, keep
`RunCommand` unused and work through written steps: the remote desktop upload
path, the site directory, and the security group allow list
(`references/file-transfer-diagnosis__transfer-methods.md`).

## How to run

The agent runs only these entry points; never assemble `aliyun` command lines
by hand, because the scripts own the parameters, the timeouts and the retry
policy.

| Task | Command |
|---|---|
| Check credentials and account | `python scripts/axes/file_transfer_diagnosis/sts_token.py` |
| Route a symptom with no cloud call | `python scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py classify --symptom "<customer words>" --error-text "<exact error>"` |
| Gather cloud evidence and report | `python scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py collect --region-id <region> --instance-id <id> --symptom "<customer words>" --paths <upload target>` |
| Plan the in-guest inspection | `python scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py guest-plan --region-id <region> --instance-id <id> --paths <target>` |
| Send one approved command | `python scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py guest-plan --region-id <region> --instance-id <id> --command "stat <target>" --confirm` |
| Fetch a command result | `python scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py invocation --region-id <region> --invoke-id <id>` |

`collect` needs `--region-id` and `--instance-id`; it echoes both back under
"Automatically filled parameters" so the customer can see what was assumed.
Ask for the instance id and region rather than guessing them. If the account
preflight fails, pass `--account-note` with whatever the customer stated and
say in the report that the account is unverified.

Required inputs beyond the ids: the transfer direction (who moves what to
where), the client and protocol in use, the exact error text, and the file size
and count. `classify` returns a `no-match` result and asks for these instead of
inventing a cause.

## Observability

Every CLI call carries `--user-agent` built from the template
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, where `{skill}` resolves to
`alibabacloud-ecs-high-frequency-issues: file-transfer-diagnosis` and `{session-id}` is a 32-character
hex value generated once per script run with `uuid.uuid4().hex` and printed at
the top of the run. Each call also has a bounded timeout, retries only
transient failures with backoff, and masks credential-looking text before it is
printed. Credentials come from the ambient CLI profile or an instance role
only; the scripts never take, read, echo or store a key or secret.

## Decision tree

Full definitions live in `references/file-transfer-diagnosis__symptom-taxonomy.md`. Enter at B0 and stop
at the first branch that fits.

| Branch | Customer situation | Where it goes |
|---|---|---|
| B0 | The FTP or upload belongs to another product | State the product boundary, route out, stop |
| B1 | No transfer path chosen; "where is the upload button", "what is my FTP password" | Correct the assumption, give the method selection table |
| B2 | Cannot connect at all | Instance state, security group allow list, customer-side port test |
| B3 | Connects but slow or stalled | Declared peak versus observed rate, region pair, link quality |
| B4 | Transferred but refused or invisible | Path, permission or space, resolved with an inspection command or pasted output |
| B5 | Protocol mode detail: active versus passive, concurrency, client fit | Prefer SFTP on one port, otherwise the passive range |
| B6 | Console artifacts and bulk transfer across regions or accounts | State the capability limit, propose the documented alternative |

## Answer contract

Report in this order, using only values the scripts actually returned:

1. **Symptom classification** with the branch id and what was matched.
2. **Evidence collected**, item by item, each with its source: cloud query,
   in-guest command output, or customer-pasted text.
3. **Conclusion**: the root cause and its confidence. Mark anything inferred
   from a single reading as inferred, and say so.
4. **Actions**: the allow list to check, the commands to run, and any handoff.
5. **Risk and backup notes**: a manual snapshot before anything inside the
   instance changes (`https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot`,
   billing `https://help.aliyun.com/zh/ecs/product-overview/snapshots-1`).
6. **Gaps**: what could not be measured, verbatim from the script output.

Close with the `STATUS:` and `NEXT_ACTION:` lines the script printed. When the
status is `DEGRADED` or `FAIL`, say which reading is missing and what to run;
never present a solved problem that the evidence does not show.

## Handoffs

Identify these, name the owner, and do not answer them here. Full wording is in
`references/file-transfer-diagnosis__boundary-and-handoff.md`.

| Signal | Route to |
|---|---|
| SSH or remote desktop fails with no transfer involved | the remote connection skill for that protocol |
| Account locked after failed logins, key pair or password changes | `alibabacloud-ecs-high-frequency-issues: login-credential-repair` |
| Packet loss, latency, cross-border route as the complaint | `alibabacloud-mtr-network-diagnosis-customer` |
| Bandwidth peak, temporary upgrade, billing mode | `alibabacloud-ecs-high-frequency-issues: bandwidth-modify-guide` |
| Disk space or inode exhaustion | the disk capacity skill |
| A disk that grew in the console but not in the OS | `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis` |
| Instance stuck starting or stopping | the instance state skill |
| Disk latency or throughput below spec | the disk IO performance skill |
| Overdue balance stopped the instance or its bandwidth | account and billing support |
| Web Hosting FTP accounts, Wuying Cloud Desktop, order review uploads | that product's own console and support |

## Authorization errors

When a query is refused, name the missing action and point at the policy in
`references/ram-policies.md`. Report the condition with the literals
`NoPermission` or `ImplicitDeny` as returned, and quote the returned code; do
not restate it with any other term. Never ask the customer for a key or secret
to work around a denial: the fix is a policy attached to the profile the CLI
already uses.

## Known limits

This skill has no observer-side dial testing and no third-party MTR platform,
and it cannot read the bandwidth usage series or the security group rule list
with a verified action. Those stay as console readings requested from the
customer. The script prints this list under **Gaps** on every run, so repeat it
rather than paraphrasing it away.

## Reference index

| File | Contents |
|---|---|
| `references/ram-policies.md` | Minimal policy, one statement per called action |
| `references/file-transfer-diagnosis__symptom-taxonomy.md` | B0 to B6 definitions and intake questions |
| `references/file-transfer-diagnosis__transfer-methods.md` | Method selection, port matrix, documented paths |
| `references/file-transfer-diagnosis__error-signatures.md` | Error text to branch, in script order |
| `references/file-transfer-diagnosis__root-causes.md` | Cause chains for each branch |
| `references/file-transfer-diagnosis__boundary-and-handoff.md` | Boundary wording and the overseas rule |
| `references/file-transfer-diagnosis__customer-commands.md` | Whitelist plus manual-lane commands |
