# Layered RDP diagnosis checklist (fixed order, reproducible)

The customer states a symptom ("remote desktop won't connect", "black screen",
"authentication error"), never a root cause. This skill walks the same layers
every time so two runs on the same instance give the same answer. The order
below is the order the entry script and the operator follow. Each layer names
the evidence source, the pass/fail reading, and what to do when it fails. Cloud
API cannot see inside the guest, so layers 4 and 5 depend on the gated in-guest
query channel described in [guest-query-commands.md](windows-rdp__guest-query-commands.md);
when that channel is unavailable the layer degrades to a manual reading instead
of guessing.

## Layer 0 — Product and OS disambiguation (do this first)

Evidence: `DescribeInstances` for the locator.

* Confirm the target is an **ECS** instance, not a Simple Application Server or
  a Wuying / cloud-desktop product. Real tickets show three-way confusion
  ("is it a lightweight server?", "my cloud desktop"); if the locator resolves
  to nothing here but the customer insists the machine exists, it is likely a
  different product — hand off per [handoff-matrix.md](windows-rdp__handoff-matrix.md).
* Confirm the OS is **Windows**. `mstsc` and RDP do not apply to a Linux image;
  an SSH / Workbench timeout on Linux is a different area. A customer
  connecting with an RDP client to a Linux host will always "fail to connect"
  and no RDP check will help.

If either check fails, stop the RDP flow and route out. Do not run further
RDP layers on a non-Windows or non-ECS target.

## Layer 1 — Evidence intake (ask once, structured)

Collect, and mark any missing item explicitly rather than assuming it:

* the **error screenshot and the exact error text / code** (decides whether a
  taxonomy branch is hit immediately — see [error-code-taxonomy.md](windows-rdp__error-code-taxonomy.md));
* the exact **ip:port the customer dialed** (default 3389, but tickets show
  33890 and 16909 in use);
* the **instance id / region**;
* the customer's **own public IP** (for a narrowed allow recommendation);
* whether they have already **tried another network or another device**.

## Layer 2 — Cloud-side connection surface

Evidence: `DescribeInstances` + `DescribeSecurityGroupAttribute`.

* Instance state must be `Running`. A stopped or transitional-state instance
  is not an RDP problem — route to instance-state diagnosis.
* A reachable **public IP / EIP** must exist for the address being dialed; if
  none is returned, verify the target address or use an internal / Workbench
  channel.
* **Region**: if the instance is outside mainland China (or in cn-hongkong) and
  the client is inside it, raise the cross-border public-path possibility
  ([cross-border-network.md](windows-rdp__cross-border-network.md)).
* **Security group** ingress for the dialed port: is TCP <port> accepted, and
  from what source? A missing allow is a definitive cloud-side block. An allow
  scoped to `0.0.0.0/0` is not a block but is the usual cause of the account
  lockout seen downstream ([account-lockout-and-hardening.md](windows-rdp__account-lockout-and-hardening.md)).

## Layer 3 — In-guest channel gate

Evidence: `DescribeCloudAssistantStatus`.

Cloud Assistant readiness decides two things at once: whether the online
reset-password path works, and whether this skill can collect a guest-side
reading now. If it is not ready (offline or an over-old agent), the skill cannot
obtain layers 4 and 5 automatically: mark the run `DEGRADED`, fall back to the
client-side evidence checklist, and offer an authorized manual look. Never
fabricate a guest reading.

## Layer 4 — In-guest query (one confirmed, non-mutating command per item)

Only after telling the operator exactly which command runs, its scope, that it
is non-mutating and reversible-because-it-writes-nothing, and getting a
confirmation. Query, in this priority order:

1. **RDP service stack** — TermService / UmRdpService / SessionEnv startup and state.
2. **Actual listening port** — compare what is listening to the port dialed
   (catches a non-default port the security group still blocks).
3. **Internal firewall** — profile state and the Remote Desktop rule group.
4. **Local account** — enabled state and lockout events (local only; domain
   policy is not visible to these queries — say so).
5. **Sessions** — current console and RDP sessions.
6. **TerminalServices log** — recent LocalSessionManager errors.

## Layer 5 — Resource watermark (black-screen / lag area)

Evidence: in-guest `resource-top`, or the CloudMonitor console memory curve.
Sustained memory at 85-90%+ with a large explorer/svchost footprint is the
dominant cause behind "black screen", "frozen", "disconnected" tickets. If the
guest is wedged, even the query channel may fail to return: that is a known
degrade path, and the honest conclusion is "the system is exhausted and cannot
be read; a manual restart is the operator's step".

## Layer 6 — Wrap-up

Emit: the root-cause branch (or the short list of branches still open), the
evidence chain (which API returned what, which command returned what), the
**repair-owner attribution** (manual console step / another skill / cloud-side
uncontrollable), and the risk + snapshot advisory. Anything this skill does not
run is presented as a step with its console entry, its risk, and the "snapshot
first" note — never as a runnable command.

## Honest limits of the automated reads

* `DescribeInvocations` returns only **past** execution results; it is not a
  live meter. To know the current state you dispatch a fresh query.
* CloudMonitor memory/CPU is a periodic agent sample, not an instant value;
  when a guest reading and the cloud sample disagree, trust the guest reading
  and say which you used.
* A local-account query cannot see a domain controller's policy. Report account
  lockout findings with a stated confidence, not as a certainty, when the host
  may be domain-joined.
