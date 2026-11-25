# Decision tree

Symptom-led, not API-led. The customer's sentence picks the branch; the cloud
queries and the in-instance observations only serve to confirm or kill a branch.
Every node below names the source of its facts, because a report that mixes
"queried", "observed" and "the customer said" is not reviewable.

The order of the branches is the order of cost: rule out the documented
behaviour, then the cheapest falsifiable cloud-side fact, then the guest.

## S0 - Baseline (always, automatic)

Identity first (`sts get-caller-identity`), then `DescribeInstances` for one
locator: instance id or public address, plus the region.

The baseline prints state, OS name and type, image id, instance type with vCPU
and memory, region and whether it is a mainland region, public and private
addresses, security groups, billing and network type.

- Instance not found -> stop and confirm the region. A wrong region is the
  usual reason for an empty answer, and no symptom is diagnosed from a guess.
- State is not `Running` -> the branch closes here. While the guest releases
  processes and flushes memory nothing can be dispatched and no service can
  answer; both symptoms are expected. Say that this is the lifecycle area, hand
  off to `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis`, and note that this skill
  never calls a start, stop or reboot action.

## S1 - Routing (always)

Match the customer's own words against the five areas:

- **A** runtime or language environment, and OS compatibility
- **B** web server configuration or startup (Nginx, Apache, IIS, FTP)
- **C** container deployment (Docker, Kubernetes)
- **D** open-source site application environment (WordPress and similar)
- **E** resource pressure that explains a service or site failure

More than one area may match; that is normal, because "the site is down" is
usually reported before anyone knows which of them it is. No area matching at
all is a `STATUS: DEGRADED` result with one instruction: ask what the customer
sees and re-run with their sentence.

Two filters run at the same time as the routing:

1. **Handoff match** - if the wording belongs to another owner (extension
   install, instance lifecycle, disk capacity or IO, security, network path,
   filing, billing, RAM, migration, backup, cluster, third-party panel, sales),
   the report says so at this point rather than after a full investigation. See
   `references/web-service-runtime-config__handoff-matrix.md`.
2. **Expected-behaviour match** - the documented mechanisms that look like
   faults. Ruling these out first is what prevents the long dead-end threads.
   See `references/web-service-runtime-config__non-fault-mechanisms.md`.

Then the quoted error string is interpreted - see S2F.

## S2A - Runtime or language environment

First question: which OS release is this, actually? The image id from S0 answers
it, and several tickets in this tier were "product not supported" reports that
were really an unsupported release assumption. `references/web-service-runtime-config__os-runtime-support.md`
holds the support facts, including where the honest answer is "there is no
official statement".

Windows is a different branch, not a smaller one: the console one-click scripts
are for Linux releases, so the manual installation path is the answer, and "the
product is unsupported" is the wrong conclusion.

Guest half: runtime version and installed package facts. Both are **pending**,
so they are customer-run. Where the failure is inside the customer's own script,
ask for the script body before naming a cause - in one ticket, forcing the
interpreter did not help and a Python 2 print statement was the whole problem.

## S2B - Web server configuration or startup

Order matters here, and it is the order that produced the fewest wasted rounds in
this tier's tickets:

1. inbound rules for the port (cloud query, no confirmation needed);
2. whether anything listens, and on which address (customer-run observation);
3. configuration syntax and the service's own log (customer-run);
4. only then, changes - which this skill emits as steps and never applies.

`nginx -t` is a syntax check, not a reload. A restart is never issued here. If a
version switch preceded the failure, say plainly that the switch left the service
unhealthy and that nobody had inspected the config yet.

IIS has no approved query in this batch. Where the only evidence is a console
screenshot - for example a missing handler mapping entry - report it as unread
and ask for the screenshot; do not assert the missing role as a verified finding.

## S2C - Reachability that the customer reports as "the server is down"

`Connection refused` and `Connection reset` split the problem differently, and
the split decides who is next.

- **refused** - nothing accepted the connection: no listener, a listener bound
  to loopback only, or a missing inbound rule. Check the rule first because it
  is free and fast. The platform does not block a customer's proxy port; that is
  recorded in the ticket evidence, so do not conclude it.
- **reset** - an established connection was torn down: TLS or certificate
  mismatch, an intermediate layer such as a self-hosted protection proxy, a
  security penalty, or a carrier-side block. Self-test the same address from
  inside the instance and split on the result: local passes and external fails
  goes to the outbound and compliance branch, local also fails stays on the
  service branch. The nearest ticket in this tier reached no proven cause, so
  report candidates and hand the platform-side question to a human queue.
- **timed out** - three unrelated causes look identical: Docker Hub
  reachability from a mainland region, cross-border latency, or a suspended
  pay-by-traffic bandwidth service. Separate them by asking whether the failing
  address is an outbound public destination, which region the instance is in,
  and whether the account has an unpaid balance. There is no shared root cause.

Fixed-source rules are read as outages in this tier's tickets, so when a matching
rule restricts its source, ask whether the customer is testing from inside that
range. For FTP, port 21 alone is not enough: the passive data range (Windows
default 49152-65535) has to be open in the security group **and** in the guest
firewall, or transfers fail after the control connection succeeds.

This skill reports a missing inbound rule and the console path. It never creates
or changes a rule.

## S2D - Resource pressure

Only entered when the wording or the area suggests it, because the checks cost
the customer time. CloudMonitor values are queried only when the caller supplies
the namespace and metric names; this skill does not hardcode them, since the
verified parameter set for a CMS metric name was not established for this tier.
Without them the resource area degrades with an explicit note rather than
inventing names.

`DescribeDisks` is a side witness: it says which disk the service competes with,
and capacity, inode and IO diagnosis belongs to the disk skills.

One ticket in this tier had seventeen OOM events that had killed mysqld, php-fpm
and nginx in turn. So "the web service is flaky" can be a memory conclusion, but
only after the OOM record has been read - the customer-run reading, since
`free`/`dmesg` are pending.

## S2E - Containers

Two branches, and they are checked in this order:

1. outbound image reachability. A `dial tcp` or pull timeout from a mainland
   region is the documented upstream change on Docker's side. State the
   reachability fact. Third-party mirror addresses that an agent pasted into a
   ticket are not recommendations, and are not repeated here.
2. persistence and restart policy. A database that returns to its image state
   after each restart is a missing host volume, not an intrusion. Keep both
   candidates open until the restart policy and mounts have actually been read.

Container restart policy changes, container recreation and data directory moves
are all manual, snapshot-first steps, and are outside this skill.

## S2F - Quoted error strings

Each string carries a licence to conclude something narrow, and an explicit
statement of what it does **not** license. `err_cert_date_invalid` is a
candidate branch only: no ticket in this tier reached a certificate-date
conclusion in its dialogue, and a WordPress "not secure" report turned out to be
a site-address setting. That gap is recorded, not papered over.

Verbatim strings customers pasted (`SyntaxError: Missing parentheses in call to
'print'`, `symbol lookup error: php-fpm: undefined symbol: zip_libzip_version`,
`java.net.NoRouteToHostException`, `dial tcp`) are matched as-is so the skill
recognises them instead of paraphrasing them away.

## S3 - Snapshot-first gate

Any manual repair step that touches files, system libraries, roles or a data
directory requires a snapshot beforehand, quoted to the customer with its billing
note, plus a reboot where the fix needs one. `CreateSnapshot` runs behind
announce-and-confirm; deleting a snapshot never runs here.

## S4 - Output

The report separates three things and never blurs them:

- what was queried (cloud, automatic);
- what was observed inside the instance, and by whom (approved gated call, or a
  customer-pasted reading);
- what remains unread, with the command or the question that would settle it.

Then the manual steps in cost order: inbound rule, listener, configuration,
resource, compliance or billing handoff. `STATUS: OK` means the evidence list is
complete enough to act; `STATUS: DEGRADED` means at least one item is unread and
names how to get it; `STATUS: FAIL` means the report cannot be used yet.
