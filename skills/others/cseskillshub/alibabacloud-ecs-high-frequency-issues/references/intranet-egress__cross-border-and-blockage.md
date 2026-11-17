# Cross-Border Paths and Regional Blocking

Wording, evidence requirements and hard limits for the two attribution classes
this skill cannot fix: `external-link` and `external-carrier`. Both describe
faults outside the cloud. The value this skill adds is a **correct, consistent
explanation delivered immediately**, plus an honest statement of what cannot be
proven from here.

## Cross-border branch

### When it applies

Selected when the path crosses the Chinese mainland border:

- Instance in a mainland region, target outside it, egress direction.
- Instance in an overseas region, client on the mainland, ingress direction.

Region classification: every `cn-` region is mainland **except** `cn-hongkong`;
any region not starting with `cn-` is overseas.

### Evidence required before attributing

Never attribute a timeout to the cross-border link on the strength of a region
alone. Require:

1. The instance region, read from the located instance.
2. The target location, either declared by the customer or operator, or matched
   against a known-overseas endpoint hint.
3. Ideally, an asymmetric observation: a domestic endpoint reachable while the
   overseas endpoint times out, from the same instance, at the same time.

When the target location is `unknown` on a mainland egress timeout, emit a
warning and ask for the resolved address instead of attributing. Resolving the
name to a real address is one command in the inspection checklist.

### Typical target classes

Endpoints that commonly sit outside the mainland and therefore commonly fail
from a mainland instance:

| Class | Examples seen in real cases |
| --- | --- |
| Code hosting | `github.com`, `gitlab.com` and their asset and raw-content hosts |
| Search and platform APIs | `google.com`, `googleapis.com`, `bing.com` |
| Certificate issuance | ACME endpoints such as `acme-v02.api.letsencrypt.org` |
| Package registries | `pypi.org`, `registry.npmjs.org`, `registry-1.docker.io` |
| Public IP echo services | `ifconfig.me`, `ipinfo.io` |

The mirror direction fails too: an instance in an overseas region reaching a
mainland service such as a domestic search engine or portal.

### Wording for the customer

Explain the boundary, do not dramatize it:

- Traffic between the mainland and an overseas endpoint crosses carrier
  international exits. Congestion and routing policy on those exits vary by time
  of day and by carrier, and are outside the cloud's control.
- A timeout on such a path is therefore **not** evidence that the instance is
  faulty. Say this plainly and early; it resolves most of the customer's anxiety.
- The fastest way to demonstrate the asymmetry is to reach a domestic endpoint
  from the same instance at the same moment.

### Options the customer may evaluate

Present these as the customer's decision, each with its own billing. This skill
executes none of them and does not estimate cost.

- Use a domestic mirror or a domestic endpoint. For package repositories this is
  usually the cheapest and most reliable fix: point `apt`, `pip` or `npm` at a
  mainland mirror.
- For certificate issuance, prefer a CA endpoint inside the mainland over an
  overseas ACME endpoint.
- Relay the fetch through an instance that is itself outside the mainland. This
  is an architecture decision with its own cost and latency profile.
- Migrate the workload to a region closer to its users or to its dependencies.
- Consider an acceleration product **only** for endpoints the customer controls.
  See the hard limit below.

### Hard limit: acceleration cannot front a closed third-party SaaS

An acceleration product accelerates traffic to endpoints the customer can name
and own. It cannot front a closed third-party SaaS whose server addresses are
chosen by that provider and change without notice. Code-hosting SaaS is the
canonical example.

**Never promise that acceleration will fix access to a third-party SaaS.** This
is a firm boundary, and reversing it later costs far more credibility than
declining up front. When the target is a third-party SaaS, say the option does
not apply and move to mirrors, relays or region migration.

### What this skill cannot prove

State the uncertainty rather than resolving it falsely:

- No live link measurement is performed. There is no probe capability here, so
  the skill cannot report current loss, latency or the state of any carrier
  path.
- Platform-side observation and customer observation frequently disagree. A probe
  from one vantage point can show no loss while the customer's own test from
  another address shows total loss. **Both can be true**, because different
  client addresses are assigned different carrier paths. Report both
  observations, name the disagreement, and do not pick a side.
- Recovery time on a congested international path is not predictable. Do not
  quote one.

## Regional and carrier-level blocking

### The signature

The combination that points here:

- Error class is `reset` - the customer sees a connection reset, not a timeout.
- The failure is seen from **one** region or province.
- It affects **several carriers** in that region while other regions work
  normally.

A reset means something answered with a RST, so the packet reached an endpoint
or a middlebox. That is what separates this from a silent drop.

### Evidence to collect

Two items, and they must come from the **failing client machine**, not from the
instance:

1. The client's egress public address with its region and carrier. A public IP
   echo service returns all three in one request.
2. A capture of the error that includes the address bar, so the failing URL and
   the exact error text are both visible.

Then compare reachability from another province or another carrier. Without that
comparison there is no evidence of a regional pattern - only one customer's one
failure.

### Wording and limits

- Report the pattern, not a culprit. Name the observation: reachable from some
  regions, reset from others, across multiple carriers in the failing region.
- The cloud can neither confirm nor lift a carrier-side or regional block. Do
  not assert that a specific block exists, and do not assert that it does not.
- The customer's path is to contact the carrier. Response times vary and are not
  under anyone's control here.
- `VERDICT: NEED-HUMAN` is the correct ending. This branch does not resolve.

## Adjacent cases that are not this branch

Do not fold these into a cross-border explanation:

| Case | Correct handling |
| --- | --- |
| Anti-DDoS blackhole or cleaning status | No query entry point. Escalate to a support ticket with the evidence bundle. Make no claim about whether a block is in force. |
| Underlying host incident, unexpected restart | Same: escalate with evidence. |
| Instance has no public address and no NAT gateway | That is `cloud-config`, not a link problem. Report it as such. |
| Zero outbound bandwidth on a fixed public address | `cloud-config`. |
| Client-side hosts file, local DNS cache, browser cache | Client-side. Provide the self-check list and stop. |
| Changing a public IP, converting to an EIP, buying bandwidth or an acceleration product | Console changes owned by the resource holder. Explain applicability, state that the operation may be irreversible and may carry billing or discount consequences, and let the customer decide. |

A note on address changes: some instances cannot have their public address
changed directly after a short window following creation, and promotional
pricing may not survive a configuration change. When a customer asks about
changing an address, state that these constraints exist and must be checked in
the console - do not quote a window or a price from memory.

## Handoff bundle

When this branch ends in escalation, hand over:

- Instance identity, region and region class, state, addresses, security groups.
- The probe: direction, target, resolved target location and how it was
  determined, port, protocol.
- The error class and the customer's verbatim error text.
- Every security group rule that matched or was a candidate, quoted as read back.
- The VPC path: VSwitch CIDRs, route tables, NAT gateways, SNAT coverage.
- The degradation log, naming any query that failed.
- The client-side observations, including the egress address and carrier if
  collected, and any disagreement between platform-side and customer
  observation.

That bundle is what makes an escalation actionable on the first round instead of
the fourth.
