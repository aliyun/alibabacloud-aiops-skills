# Database-on-ECS connectivity decision tree

Ordered by the root-cause frequency measured on the 1009 tickets merged into
this tier. Walk the layers top-down; stop at the first layer whose evidence
explains the symptom, but keep collecting the cloud-side layers anyway because
they are free. Each layer names its evidence source: `api` (cloud query the
entry script runs), `probe` (auto-dispatched whitelisted guest command, per-call
confirmation), `human` (customer runs and pastes; `explain` interprets),
`ask` (information to request from the customer).

## Layer 0 - Account and instance state (before any network talk)

| Check | Source | Verdict ids |
| --- | --- | --- |
| Instance exists in this region and is Running | api: `DescribeInstances` | `VERDICT_INSTANCE_STOPPED`, `VERDICT_INSTANCE_NOT_FOUND` |
| Scheduled expiry, release or system events pending | api: `DescribeInstancesFullStatus` | `VERDICT_EXPIRY_PENDING` |
| Overdue bill locking pay-as-you-go resources | ask + console: billing center; this skill does not query bills | hand-off: commercial channel |

Tickets showed customers "fixing" a dead-during-reboot service by restarting
the instance, or chasing a "database down" that was an overdue account.
Confirm state first, and say so when the evidence forces you to.

## Layer 1 - Network reachability to the port

Ask for: the client's egress IP, whether it is the instance public IP or a
domain in front, the port the client actually dials, and the raw error text.

Error semantics decide the branch (see error-signatures.md (in alibabacloud-ecs-high-frequency-issues)):

* `Connection refused` (client gets an instant RST) -> something answers on the
  path but no listener accepts -> Layer 2/3. A refused connection is NOT a
  security-group problem.
* `timed out` (client hangs, then fails) -> packets die quietly: blocked by a
  security group / guest firewall / third-party suite, wrong route, or the
  instance is stopped -> Layer 2 and 4.
* Name-resolution failures -> client-side or DNS; not an instance fault.

## Layer 2 - Cloud-side allow-list

| Check | Source | Verdict ids |
| --- | --- | --- |
| Which security groups the instance binds | api: `DescribeInstances` | `VERDICT_NO_PUBLIC_IP` |
| Whether the bound groups actually allow the port from the client IP | human: console rule list (rule-detail API not verified for this tier) | `VERDICT_SG_PORT_BLOCKED` |
| Port number consistency: SG opened 40731 while the client dials 3306; NAT/portal mappings | ask + human | `VERDICT_PORT_MISMATCH` |
| Newly added rules taking effect late; a rule change minutes ago | ask (recent edits), retest after minutes before deeper digging | `VERDICT_PROPAGATION_DELAY` |

The customer pastes the group id(s) and rule rows; report the exact missing
ingress entry as text guidance. Rule editing stays manual: this skill never
calls any security-group mutation.

## Layer 3 - Listener and bind inside the guest

| Check | Source | Verdict ids |
| --- | --- | --- |
| Is anything listening on the port | human: `ss -antp \| grep -w <port>` | `VERDICT_NOT_LISTENING` |
| Listening on `127.0.0.1` only (bind-address / `protected-mode yes`) | human + explain | `VERDICT_BIND_LOCALHOST` |
| SQL Server dynamic port after a password reset or service reinstall (1433 -> random) | human: `Get-NetTCPConnection`, SQL Server Configuration Manager | `VERDICT_DYNAMIC_PORT` |
| Service not started / not enabled at boot | human: `systemctl status`, Windows services | hand-off: instance-state tier for boot failures |

## Layer 4 - In-guest packet filters and third-party suites

| Check | Source | Verdict ids |
| --- | --- | --- |
| firewalld active zones/services/ports; `iptables -nL` chains | human + explain | `VERDICT_GUEST_FIREWALL` |
| Third-party security suites with their own port allow-lists | ask + human | `VERDICT_THIRD_PARTY_FW` |
| Kernel connection-tracking table full dropping SYNs (`timed out` with no firewall rule changed) | human: `dmesg \| tail -50` | `VERDICT_CONNTRACK_FULL` |

Disabling a firewall is a service-affecting edit: report the exact missing
allow-entry, never the flush command, as the change path.

## Layer 5 - Database authentication and grant layer

The network is proven; the server itself refuses the account.

| Check | Source | Verdict ids |
| --- | --- | --- |
| MySQL/MariaDB: user row grants the client host (`%` vs `localhost`); `bind-address` in the config file | human: config path + `SELECT` grant check, run by the customer | `VERDICT_HOST_GRANT` |
| SQL Server: mixed-mode authentication enabled, `sa` (or target account) enabled with a password set; service restart needed after the change - human step | ask + guidance | `VERDICT_AUTH_MODE` |
| Redis: `requirepass` mismatch; client not sending AUTH | human: config check | `VERDICT_REQUIREPASS` |
| Password changed server-side but the application connection string still carries the old one | ask | `VERDICT_CREDENTIAL_DRIFT` |

All grant, account and authentication-mode changes stay manual; the report
emits the check-and-fix procedure and stops there.

## Layer 6 - Capacity and resource pressure masquerading as "connection failed"

Web apps often render a capacity failure as "database connection failed", and
MySQL refuses to start when the disk or the memory is gone.

| Check | Source | Verdict ids |
| --- | --- | --- |
| Disk 100 percent full | probe: `df -h`, or human paste | `VERDICT_CAPACITY_FULL` |
| Inodes exhausted despite free bytes | probe: `df -i` (Linux; NTFS has no equivalent - mark confidence) | `VERDICT_INODE_FULL` |
| Deleted-but-still-open log holding space | probe: `lsof +L1` | `VERDICT_DELETED_OPEN` |
| Out-of-memory killed the database process | human: `free -m`, OOM lines in the guest log; api: memory metric when the CloudMonitor agent provides it | `VERDICT_OOM_PRESSURE` |

On any capacity verdict: snapshot first (gated), then hand the cleanup to the
ECS disk-capacity and inode tier (skill id to confirm; see the note at the end
of this file). Do not delete anything here.

## Layer 7 - Client-side and link path

Cloud side is all green -> the problem is upstream of the instance.

* Customer local network or WiFi cannot route to the target at all - MTR from
  the client machine (their side).
* Local software intercepting DNS or the port (proxy/VPN/antivirus).
* Domain resolves to an old IP after a migration.
* Intermittent redis timeouts with healthy server metrics - suggest capturing
  both ends when it reproduces; without that evidence the honest verdict is
  `VERDICT_NEEDS_CLIENT_EVIDENCE`, not a guess.

## Layer 8 - Security exposure and ransom patterns

A database port wide open to `0.0.0.0/0` with weak credentials is both a
finding and, in tickets, the prequel to an encryption attack.

| Check | Source | Verdict ids |
| --- | --- | --- |
| DB ports 3306/6379/1433/27017/5432 open to the whole internet | human: security-group rule list + explain | `VERDICT_PUBLIC_DB_PORT` |
| Ransom notes, renamed database files, attacker "backup" dumps in the data directory | human paste + explain | `VERDICT_RANSOMWARE_PATTERN` |

On exposure: emit the hardening checklist from
security-hardening-checklist.md (in alibabacloud-ecs-high-frequency-issues). On a
ransom pattern: gated snapshot to preserve the scene, never pay, recovery goes
to a third-party data-recovery specialist via the cloud marketplace, rebuilding
via re-initialize-disk is a documented manual step. This skill never cleans,
deletes or decrypts.

## Confidence discipline

* Every verdict above carries the evidence line that produced it; an absent
  reading is reported as `not visible at this layer`, never inferred.
* NTFS has no inode concept: an inode verdict is Linux-only, and the report
  says so.
* A propagation-delay verdict is provisional until the customer retests; the
  confidence label is `LOW`, and the report states what would raise it.
* When two layers are consistent with the same symptom, list both with the
  test that separates them, in order of ticket frequency.
* Verdict ids whose source column is `api` or `probe` are emitted mechanically
  by the `explain` and `probe` subcommands from real command or API output. Ids
  whose source is `human` or `ask` are asserted by the agent only after reading
  pasted output or an explicit customer answer, and that subset is frozen as
  `VERDICT_AGENT_ASSERTED_ONLY` in `scripts/axes/db_on_ecs_diagnosis/_constants.py`; the scripts never
  emit them from the absence of evidence, because "not visible at this layer"
  is a different statement from "blocked at this layer".

## Hand-off target verification

Supplied by this tier's evidence and safe to name in a report:
`alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis`,
`alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis`,
`alibabacloud-ecs-high-frequency-issues: resource-bottleneck`, `alibabacloud-ecs-diagnose`.

Not supplied, so named by scope with the id left open: the disk-capacity and
inode tier (Layer 6 cleanup) and the remote-login entry tier (the OS-level
login channel, upstream of this whole tree). Confirm the identifier against the
sibling-skill list before writing it into a hand-off sentence; do not coin one.
