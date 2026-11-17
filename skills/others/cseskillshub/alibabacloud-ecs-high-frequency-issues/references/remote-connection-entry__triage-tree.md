# Triage Tree — ECS Remote Connection Entry (protocol unspecified)

Knowledge backing [`../scripts/areas/remote_connection_entry/ecs_remote_connection_triage.py`](../scripts/areas/remote_connection_entry/ecs_remote_connection_triage.py).
This skill is the **first stop** for "I cannot connect to my ECS instance" when the
customer has not said which protocol (SSH or RDP) or which layer is failing. It is a
**splitter, not a deep-dive**: every step either produces an evidence-backed verdict
for this layer, or identifies a different area and hands it off.

Operating mode: **read-only**. Every cloud query is a `Describe*` / `GetCallerIdentity`
call. Nothing in this tree ever writes a cloud resource, and nothing is ever executed
inside the instance — guest checks are printed for the **customer to run** and paste back.

---

## Channel semantics (why the cross-test works)

The three access channels reach an instance through **different paths**, so comparing
which ones fail is itself the strongest signal available. This is the core of the tree.

| Channel | Where the client runs | Needs public IP on the instance | Subject to the security group | Subject to in-guest software / firewall |
|---|---|---|---|---|
| VNC (console) | Browser, via the console | No | **No** | **No** |
| Workbench / session manager | Browser, via an Alibaba Cloud service | No (private path available) | Yes — must allow the service source ranges | Yes |
| SSH / RDP client tool, bastion | Customer's own machine or network | **Yes** (public IP or EIP required) | Yes — must allow the customer egress IP | Yes |

Consequences used below:

- **VNC is the only channel not gated by the security group or by in-guest software**, so
  it is the universal fallback and the correct place to run guest self-checks.
- **"Console works, my local tool does not" is not a contradiction.** The console channel
  does not depend on the customer's egress IP being in the authorized source CIDR, while a
  local SSH/RDP client does. That pairing points at the source-CIDR or the local network,
  not at a server fault.
- If Workbench also fails while VNC works, the in-guest remote service (sshd / RDP
  listener) or the guest firewall is suspect, because both channels that do touch it fail.
- Third-party SSH and RDP clients require the instance to hold a public IP or an EIP. A
  VPC-only instance with no EIP simply cannot be reached from the internet; that is a
  finding, not a fault.

> Source ranges for the Workbench service channels and the exact security-group shape are
> documented in the Workbench overview and the security-group quick-start guide linked
> from [help-links.md](remote-connection-entry__help-links.md). Always relay the documented ranges; never invent a
> CIDR for the customer.

---

## S0 — Collect inputs

Before any call, obtain: instance id **or** public IP, region, the client tool in use,
the exact error text, and whether the console/VNC channel works. Ask once for anything
missing; never guess a region.

Guided local checks the **customer** runs at this stage (see
[guest-selfcheck-commands.md](remote-connection-entry__guest-selfcheck-commands.md)):

- `curl cip.cc` → the customer's own egress public IP (needed for the S3 comparison).
- `telnet <public-ip> <port>` → distinguishes silent drop from refusal.
- `ssh -v root@<public-ip> -p <port>` → shows which stage fails (connect / handshake / auth).

## S1 — Ownership and identity

Calls: `sts:GetCallerIdentity`, `ecs:DescribeInstances` (by id, then by public IP, then
by EIP).

| Observation | Verdict | Action |
|---|---|---|
| Address resolves to no instance visible to this credential in this region | `OUT_OF_SCOPE_IP` | **Stop.** It may be another provider's server or another account's asset. Ask the customer to confirm the owning account and region, or to contact that provider. Do **not** sweep other regions hunting for it. |
| The instance lookup itself errored (permission or credential) | `INSUFFICIENT` | Not evidence of absence. Name the missing permission, then re-run. A query that failed is never reported as "asset not found". |
| Found | — | continue to S2 |

## S2 — Instance state and protocol split

From the located instance: `Status`, `OSType`, public IP / EIP, bound security groups.

| Observation | Verdict | Action |
|---|---|---|
| `Stopped` | `INSTANCE_NOT_RUNNING` | Guide a manual console start. A stopped instance answers nothing. |
| `Stopping` / `Starting` | `INSTANCE_NOT_RUNNING` | A normal stop runs Running → Stopping → Starting → Running and takes **up to 10-15 minutes without manual intervention**; in-guest processes shutting down cleanly are the usual wait. Offer the VNC link so the customer can watch progress. Beyond that window → hand off `instance-state`. |
| `Running`, `OSType=linux` | — | SSH, default port **22** |
| `Running`, `OSType=windows` | — | RDP, default port **3389** |
| Client tool speaks SSH but the image is Windows | `PROTOCOL_MISMATCH` | Windows ships **without** an SSH listener enabled, so `Could not connect ... (port 22)` is the expected outcome. Send the customer to RDP 3389; enabling OpenSSH on Windows is a manual in-guest task. |
| `Running`, no public IP and no EIP, customer connects from the internet | `NO_PUBLIC_PATH` | Use the internal network / a jump host, or associate an EIP in the console themselves. |

Always declare an auto-defaulted port, e.g. "port auto-defaulted to 22 from the Linux OS
type". A custom SSH port (for example 10022) must appear **consistently** in the client,
the security group and the guest listener — three places, and a mismatch in any one of
them produces a generic timeout.

## S3 — Security-group port and source CIDR

Call: `ecs:DescribeSecurityGroupAttribute` for every bound group. Rules are matched
first-hit: ascending `Priority`, and at equal priority a `Drop` rule wins over an
`Accept` rule. Only **ingress** rules for the target protocol/port matter here.

| Observation | Verdict | Action |
|---|---|---|
| No ingress `Accept` covers the target port | `SG_PORT_CLOSED` | Show the enumerated rules. The customer adds the rule in the console; **this skill never writes security-group rules**. |
| An `Accept` covers the port, but no authorized source CIDR contains the customer egress IP | `SG_SOURCE_MISMATCH` | This is the single most common "I already opened the port" case. Show the listed CIDRs next to the egress IP from `curl cip.cc`; the customer fixes the authorized source in the console. |
| A `Drop`/`Reject` rule matches first | `SG_PORT_CLOSED` | Report the priority inversion — a high-priority deny silently overrides a later allow. |
| Port allowed and source covered | — | Cloud path is open; continue to S4. |

**Hard limit of this step:** an open security group does **not** mean the port is
reachable. The guest's own iptables/firewalld is invisible to every cloud API, so S3 can
only ever clear the cloud side, never confirm reachability. Say so rather than implying
the customer is wrong.

## S4 — Fallback channel, then the guest

Calls: `ecs:DescribeInstanceVncUrl`, `ecs:DescribeCloudAssistantStatus`.

- VNC link is offered whenever the instance is `Running` — it is the channel that works
  even when everything else fails, and it is where the guest checks below must be run.
- Cloud Assistant offline is **not** shown to the customer as a technical detail; it is
  translated into the usable fact that the passwordless console channels (Workbench,
  session manager) are unavailable, so use VNC. It also explains why an *online* password
  reset would fail, since that path depends on the agent.

Then run the **customer-side** comparison and read the result:

| VNC | Plain command line | GUI tool | Conclusion | Verdict |
|---|---|---|---|---|
| ok | ok | fails | Tool-side (WebSocket/proxy/compatibility) or local network | `TOOL_LOCAL` |
| ok | fails | fails | In-guest service, listener, host firewall or credentials | `GUEST_LIKELY` |
| fails | fails | fails | Cloud path or the whole system is unresponsive | go to S5 |
| login succeeds, then the session is rejected at authentication | — | — | Authentication was reached and refused | `CREDENTIAL` |

Guest self-check list to hand to the customer (they run it, they paste it back) is in
[guest-selfcheck-commands.md](remote-connection-entry__guest-selfcheck-commands.md). Reading it:

| Evidence in guest output | Meaning | Next |
|---|---|---|
| `sshd` inactive/failed (on Ubuntu/Debian the unit is `ssh`, not `sshd`) | Service down | Customer starts it; then re-test |
| Nothing listening on the expected port | Listener moved or not started | Check `/etc/ssh/sshd_config` `Port`, then restart the SSH service |
| iptables/firewalld shows a DROP or REJECT on the port | Guest firewall overrides an open security group | Customer adjusts the guest firewall; guidance only |
| `/var/log/secure` (Debian-family: `/var/log/auth.log`) shows `fork: Cannot allocate memory` | Process-slot / memory exhaustion breaks the handshake, often with `Connection reset by peer` | Hand off to the documented process-limit guide |
| Disk or inode usage at 100% | A full root filesystem breaks logins silently | Hand off `disk-capacity` |
| Only the security group looked wrong, guest clean | Cloud-side rule only | Fix the rule in the console and stop |

**Credentials branch.** Authentication-stage errors (`Permission denied`,
`Too many authentication failures`, `No supported authentication methods available`)
mean the path works and the secret does not. Guide the customer to the console credential
flow, and state the effectiveness rules, because they are a frequent source of "I changed
it and nothing happened":

- An **online** password reset needs no reboot but depends on the Cloud Assistant agent;
  guest security software blocking that agent is the common reason it fails.
- An **offline** reset, and binding / unbinding a key pair from the console, take effect
  **only after an instance restart**.
- Editing `sshd_config` (for example `PubkeyAuthentication`, `PasswordAuthentication`)
  takes effect only after the **SSH service** is restarted — a different action from an
  instance restart, and confusing the two is a known dead end.
- **Never** collect, store, or test the customer's password or private key. Console
  credential reset guidance is the only permitted output on this branch.

## S5 — Saturation / hang, and the remaining exits

Call: `cms:DescribeMetricLast` (latest `cpu_total`), optional via `--skip-metrics`.

| Observation | Verdict | Action |
|---|---|---|
| CPU pinned at/near the ceiling, and every port and every panel is unreachable | `SATURATION_HANG` | The connection failure is a **symptom** of a wedged system. Relay the snapshot-first restart notice (a manual console action by the customer) and hand off
`area:resource-bottleneck`. Recommend installing `atop` afterwards so the next incident is diagnosable. |
| Monitoring skipped, denied or empty | — | State the gap explicitly and judge from symptoms only. Never assert a metric value that was not returned. |
| VNC / console works, but the public address is dead from outside, pay-as-you-go bandwidth | `OVERDUE_PATTERN` | A stopped-over-balance bandwidth is a known cause. This skill has **no** balance or overdue query capability, so it must not assert the cause: point the customer to check and top up in the billing console themselves. |
| Nothing pinned down (no egress IP, no error text, channels untested) | `INSUFFICIENT` | List the specific missing facts and the next manual check; attach the evidence already gathered so a human ticket does not repeat the work. |

## X — Intrusion suspicion, reachable from any step

When the customer reports an unknown login, an unfamiliar source IP, or "we are under
attack", **stop presenting connection triage as the story**: hand off on the security
area and emit the hardening checklist. Pass `--intrusion-suspect` in that case — keyword
matching on the error text is English-only and must not be the only trigger.

Hardening checklist to relay, in order: change the instance password and rotate key pairs
from the console; restrict the SSH/RDP source CIDR to known egress IPs; upgrade exposed
software and patch via Security Center; take regular snapshots; report malicious outbound
activity through the abuse-report page.

Ownership investigation of a third party's IP is out of scope: the owning account of another
customer is private, and even a human agent can only say "that address is not yours".

---

## Handoff routing table

This skill **identifies** these areas and transfers them; it never diagnoses them.

| Detected symptom | Target |
|---|---|
| Instance will not start, or stuck in a transitional state past 10-15 min | `area:instance-state-diagnosis` |
| CPU / disk IO / BPS saturation, the instance is wedged | `area:resource-bottleneck` |
| Guest check shows a full filesystem or exhausted inode pool | the disk-capacity skill |
| Expansion completed but the partition / filesystem did not grow | `area:disk-expand-diagnosis` |
| Suspected intrusion, unknown logins, abuse from the asset | security channel: support ticket plus Security Center, abuse report page |
| Address belongs to another provider or another account | out of scope — stop |
| Billing, refunds, top-up as a commercial action | the billing console, by the customer |
| Any destructive action: force restart, delete snapshot, reformat, overwrite rules | human, in the console, by the customer |

Handoff sentence template — name the area, name the target, and carry the evidence:

> "Monitoring and the channel comparison show <evidence>, which is the <area> area rather
> than the connection path itself. Please continue with `<target-skill>`; the evidence
> already collected in this report can be reused as-is."

---

## What this tree deliberately cannot do

- It cannot see inside the guest: process-level memory and IO, `/var/log/secure`, the
  real sshd listener, and iptables/firewalld state are all invisible to cloud APIs. Only
  the customer, inside a VNC session, can produce that evidence.
- It cannot touch the customer's own network — local proxy, VPN, corporate firewall and
  ISP path are unreachable for any tool. Only the cross-test matrix narrows them, which is
  exactly what a human agent does by asking.
- It cannot prove account delinquency; no verified read-only API was available for it.
- It cannot determine who owns somebody else's IP address.
- It never performs remediation. Every fix that changes state is a console action the
  customer takes, with the risk notice attached.
