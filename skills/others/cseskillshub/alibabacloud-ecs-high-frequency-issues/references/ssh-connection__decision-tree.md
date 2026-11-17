# Diagnosis decision tree

Implemented by [`../scripts/areas/ssh_connection/ecs_ssh_diagnosis.py`](../scripts/areas/ssh_connection/ecs_ssh_diagnosis.py).
Each phase below names the calls it makes, what it concludes, and what it refuses
to conclude. Run the script; do not reproduce these steps by hand-typing
`aliyun` commands.

## Scope of this tree

This tree owns one vertical area only: **establishing and keeping an SSH or
remote-login session on an ECS instance** - timeouts, refusals, resets,
authentication failures and mid-session drops. Anything else is identified and
handed off (see the last section). A request for a general ECS inspection belongs
to `alibabacloud-ecs-diagnose`.

## S0 Inputs

Collect before running anything:

| Input | Required | Notes |
| --- | --- | --- |
| `--region-id` | yes | Every call is regional; a wrong region looks identical to an instance that does not exist |
| `--instance-id` **or** `--ip-address` | yes | An address is resolved through the public, EIP and private address filters in that order |
| `--error-text` | strongly advised | Without it there is no branch, so the run falls back to the generic establishment path and reports `DEGRADED` |
| `--ssh-port` | no, default 22 | Custom ports are common; the real port is proven in S5 |
| `--source-ip` | no | The customer's egress public IPv4; without it S3 can only report the rule, not whether it matches |
| `--fault-time` | no | Used to line the guest reading up against the console monitoring chart |
| `--login-name`, `--client-tool` | no | Distinguish root restrictions, key versus password expectations, and browser or overlay paths |

The customer obtains their egress address from a public "what is my IP" service,
never from their operating system's interface list.

## S1 Preflight

1. `sts:GetCallerIdentity` - proves the credential chain and records which account
   visibility was tested against. If this fails, stop: the report says to repair
   the local CLI profile, and no AccessKey value is ever requested or printed.
2. `ecs:DescribeInstances` - existence, `Status`, `OSType`, addresses,
   `SecurityGroupIds`, `Cpu`, `Memory`, `ExpiredTime`.

Decisions:

* **Empty result for an instance id that the customer swears exists.** Two causes
  are indistinguishable and both end this run: a different region, or an instance
  owned by a different account. There is no cross-account query. Hand off and say
  so plainly - this is the single most common way a session is wasted.
* **`Status` is not `Running`** (including `Pending`, `Starting`, `Stopping`,
  `Stopped`). SSH cannot work. Hand off to `area:instance-state-diagnosis`
  rather than diagnosing a connection that has no chance.
* **`OSType` is Windows.** Windows ships without an enabled SSH server, so an SSH
  complaint is expected to fail whatever the security group says. State that, offer
  RDP through the console path or installing OpenSSH Server as a human action, and
  mark the whole Windows conclusion as lower confidence: no in-guest command is run
  on Windows by this skill.

## S2 Triage

Map `--error-text` onto branches using [error-triage.md](ssh-connection__error-triage.md). A single
message can select two branches (`Server refused our key` is authentication, not
establishment); keep both and let later evidence decide.

## S3 Network permission layer

`ecs:DescribeSecurityGroupAttribute` per attached group, `Direction=ingress`, then:

1. **No Accept rule covers the port.** This is the root cause; nothing else matters
   until it changes. Emit the exact rule a human must add. Common in tickets where
   the customer deleted the rule themselves while "hardening" the group.
2. **The rule allows the port from `0.0.0.0/0`.** Connection is possible, but report
   the exposure as its own finding: a world-open SSH port is brute-forced, which is
   how accounts get locked and how the next symptom in this tree appears.
3. **The authorization object is not a public unicast address** (RFC1918,
   `100.64.0.0/10` carrier-grade NAT, `100.100.0.0/16`, or an address the local
   operating system reports). The rule can never match Internet traffic, so the
   customer's whitelist entry is silently dead. This is the most misdiagnosed case:
   the customer sees "I added my IP and it still fails", or "changing the group
   fixed it" when it did not.
4. **The object is a console or Workbench source range.** Only meaningful for
   sessions that originate in the web console. Treat the exact range as unverified:
   refer to the official Workbench documentation rather than hardcoding a prefix
   from a conversation.
5. **`--source-ip` was supplied and does not fall inside the object.** Say the two
   do not match and ask for a fresh egress reading, because mobile and corporate
   NAT rotate addresses.

Security-group edits are always human actions.

## S4 Capacity area

A wedged guest answers nothing, and that is indistinguishable from a network fault
from outside. This skill deliberately holds **no monitoring or metric permission**,
so it never produces a utilisation number. Instead it:

* states that saturation must be read by a human in the console monitoring charts
  for the exact failure window, and lines that up with the customer's timestamps -
  the timeline is what settles the argument about cause and effect;
* suggests the customer run `uptime`, `free -m` and a kernel-log reader over a VNC
  session and paste the output back, looking for load far above the vCPU count,
  near-zero available memory, and out-of-memory lines naming their own process;
* recommends, as human steps in this order: snapshot every disk, restart the
  instance to release resources, then install `atop` and the CloudMonitor agent so
  the next incident has history, then evaluate swap or a larger memory
  specification.

Hand off to `area:resource-bottleneck` when the real limit is disk IOPS
or throughput, and to `area:disk-expand-diagnosis` for capacity growth.

## S5 Guest evidence

Cloud API metadata cannot see a daemon's configuration, the real listening port, or
a guest firewall. Those live inside the instance only.

`ecs:DescribeCloudAssistantStatus` first. When the agent is not answering, the
channel is closed and the fallback is `ecs:DescribeInstanceVncUrl` plus a command
list for the customer to run and paste back - or nothing at all, reported as
`STATUS: DEGRADED`. Note that a guest wedged by exhaustion often stops
heartbeating, so an unanswered status check is itself a capacity signal.

When the agent is present, delivery is gated: state the exact command, what it
reads, and that it changes nothing, wait for the customer's agreement, then run
with `--guest-command <key> --guest-confirmed-by <name>`. One command per call,
`ecs:run-command` with `Type=RunShellScript`, output read back with
`ecs:DescribeInvocations` (`IncludeOutput=true`). Confirmation covers that one
command only. See [guest-evidence-commands.md](ssh-connection__guest-evidence-commands.md) for the
closed list and the refusal rule.

Interpretation notes:

* `ss -tlnp` showing no SSH socket explains `Connection refused`; a socket on
  `4522` while the customer targets `22` explains the same message.
* A commented `#PubkeyAuthentication yes` means the option was never enabled
  explicitly, which behaves differently from an active `no` - report the
  difference instead of guessing.
* A group or world writable `authorized_keys` or its directory makes OpenSSH
  ignore the file, producing `Permission denied (publickey)` with a correct key.

## S6 Authentication conclusion

Combine the error text with the reading, then produce a human fix: which option is
wrong, where it is set, what value it needs, and the required service restart.
Editing `/etc/ssh/sshd_config` and restarting the daemon is **never** executed by
this skill, even though a human support engineer would do exactly that after being
granted access. Say which part is left to the customer.

Also state the two standing misunderstandings whenever they apply:

* A key managed in the console for Workbench and the private key on the customer's
  laptop are two different credentials; a successful console login proves nothing
  about a local key file.
* The instance password is not the Alibaba Cloud account password.

## S7 Compromise indicators

Missing login shell or helper library, a `rm -rf` in the visible history, mining or
malware context, interception by Security Center, repeated lockout. Hand off to
Security Center or a human security engineer. This skill does not clean,
quarantine, restore or trace, and does not reconstruct what an intruder did.

## S8 Customer-side path

Emitted only when every cloud-side check came back clean. It is an ordered
elimination list, not a paragraph: fresh egress address, `Test-NetConnection` or
`nc -vz` to isolate TCP from SSH, VPN, proxy and antivirus off, client keepalive
arguments, browser path in incognito or with extensions disabled, overlay versus
public address A/B test, another client, another network.

The report shows the cloud-side checklist that was cleared, which is what makes the
conclusion credible; a bare "the server side is fine" is not.

## S9 Output

Every item carries its source. Actions are grouped as: completed automatically
(the Describe and Get calls), executed after confirmation (`ecs:run-command`), left
to a human, or handed off. Close with `STATUS: OK|DEGRADED|FAIL` and one
`NEXT_ACTION`.

## Handoff map

| What this skill sees | Where it goes |
| --- | --- |
| A request for a full ECS health check | `alibabacloud-ecs-diagnose` |
| Instance not `Running`, or stuck in `Stopping` or `Starting` | `area:instance-state-diagnosis` |
| Disk IOPS or throughput at the spec limit | `area:resource-bottleneck` |
| Disk or inode capacity, or a resize that did not take effect | the capacity and expansion skills of this family |
| Mining, malware, interception by Security Center, deleted system files | Security Center or a human security engineer |
| An instance in another account | the owning account, or switch credentials |
| A Windows RDP lockout or an NTFS question | a human: the checks here are analogous, not equivalent, and are labelled low confidence |
