# Error Strings and Codes: What Each One Actually Proves

Customers report symptoms; the wording on their screen is the strongest
layer separator available. This file maps that wording to the layer it
indicts. `ERROR_PATTERNS` in `scripts/areas/console_channel_diagnosis/_constants.py` carries the same
patterns, matched case-insensitively against the normalized English wording
passed to `diagnose --error-text`.

Two tiers of wording appear below, and the difference matters for how
confidently a reading is stated:

* **Tier codes** - the two error codes this capability is specified to quote:
  `Connection refused` and `InvalidDependence.GrantAccess`.
* **Observed login-layer wording** - sentences seen in real support
  conversations on this symptom area. They carry the weight of observation,
  not of a contractual code; treat them as hypotheses that the evidence
  chain confirms or refutes.

## Read this before quoting any code back

Match what the customer actually sees. If a code below is not present in
their text or screenshot, do not introduce it - "I did not see that error"
is a better report than a guessed one. Where an authorization failure has to
be described, this package always uses `NoPermission` or `ImplicitDeny`;
other denial vocabulary that a platform may return internally is normalized
to those two before it reaches a report.

## Pattern table

| Pattern key | Wording it matches | Layer indicted | Reading and lane |
| --- | --- | --- | --- |
| `grant_access_dependence` | `InvalidDependence.GrantAccess` | L2 | See "The grant-dependence code" below. Configuration dependency, not a channel outage. |
| `connection_refused` | `Connection refused` | L2 / L4 | See "The refused code" below. Answered host, no listener - run the port triad. |
| `state_unsupported` | "the current state of the resource does not support this operation" | L1 | The console refuses because of the INSTANCE lifecycle state, not because the VNC feature is broken. Read `Status` first; a stuck transition hands off to the instance-state skill. |
| `blocked_intercept` | "blocked", "intercepted", a login request refused by the page itself | L4 usually | The classic web-terminal interception wording. In the observed corpus this is nearly always guest resource exhaustion behind an otherwise healthy instance - gather the monitoring leg before anyone restarts. Weak on its own: the needle is a common English word, so it only counts together with `--symptom blocked`. |
| `no_password_prompt` | any wording containing "password" | L4 | Deliberately weak, used only as a corroborating token. The specific high-value pattern is a login form that accepts the user name, and after Enter never shows the password box at all - that is a hung-guest signature, pass `--symptom no-password-prompt` to carry it. |
| `too_many_auth_failures` | "too many authentication failures" | L4 | Repeated-attempt throttling or an in-guest lockout. Lockout state is NOT auto-inspectable here; see the lockout lane. |
| `incorrect_login` | "incorrect", "invalid account or password" | L4 | Credentials refused. Check the reset-then-restart ordering before believing the password is wrong. |
| `socket_timeout` | `SocketTimeoutException` | L4 | A timeout while the web terminal reaches the instance over the internal path, with public traffic to the instance still working, points at in-guest software rejecting Alibaba Cloud service segments (third-party tunnel software is the observed cause). Pass `--third-party-network` when the customer confirms such software. |
| `no_route` | "No route to host" | L5 usually | Nothing answered: local egress, carrier route, or a dropping ingress rule. Not a listener problem - a listener failure would answer with a refusal instead. |
| `timed_out` | "timed out", "operation timed out" | L5 / L4 | Ambiguous by design: packets never answered (L5) or the guest answered too slowly (L4). Resolve with the Cloud Assistant leg plus the monitoring leg. |

## The refused code: `Connection refused`

`Connection refused` is the most misread string on this area. It means a host
answered the SYN and said "nobody is listening here" - so the network path
worked and the port has no listener, or the listener is on the wrong address
family. Three checks, in this order (the port triad):

1. **The application's real port vs the port being used.** A web panel
   serving on one port and being called on a nearby one is the recurring
   near-miss, and the resulting complaint is "I cannot connect to my
   server", which is not what happened at all. VNC or a screenshot of the
   application's own banner settles this in one step.
2. **Security-group ingress for that port.** Outside this skill's verified
   action set: the customer reviews the rule in the console (self-check), and
   the report says "asked about", never "checked".
3. **The in-guest listener and its address family.** A service bound only to
   the IPv6 wildcard refuses IPv4 arrivals even though it is running - so an
   ssh port change that "worked" locally can still break every external
   client. Listing listeners is not on the guest whitelist for this tier:
   ask the customer to run it and paste the output into `explain`.

Layer separator worth stating plainly: the Workbench one-click path only ever
uses port 22. Move ssh to a non-standard port and exactly that one channel
breaks, while password login on the new port and VNC keep working.

## The grant-dependence code: `InvalidDependence.GrantAccess`

Seen when changing the VPC an instance belongs to, not when connecting. The
VPC is protected by a reverse-access grant chain created through the web
terminal path; the change stays refused until those grants are released.

* This is a configuration dependency, not an outage. The instance may be
  perfectly reachable.
* Releasing the grant chain is a **human console action**. This skill never
  performs it and never calls a release action - it is on the refused list.
* Explain the semantics first ("a leftover authorization chain, not a broken
  network"), then have the customer release the grants in the console and
  retry the change.
* **Honest gap:** no verified official deep link for the release path ships
  with this package. The console navigation is guidance from the support
  corpus, not a checked URL. If the customer cannot find the page, route to
  human support instead of inventing a link.

## The 403 web-terminal command-line denial

A web-terminal command-line login can fail with a 403 whose code ends in
`NoPasswordLogin` even when the password is correct. That is an
**authorization** result, not a credential result: the command-line path
authenticates through the OpenAPI, so a sub-user whose AccessKey lacks the
terminal-session permission is refused before the password is ever consulted.

* First check `check-auth` / the identity step: the report already flags a
  RAM sub-user caller.
* Then compare the sub-user's policy against
  [ram-policies.md](ram-policies.md).
* Do not tell this customer to reset the password. Resetting it cannot fix a
  missing permission grant, and the reset itself is a human console action
  here.

## Login wording that is not an error code

Observed sentences that customers quote verbatim, and their reading:

* "the remote connection was disconnected, the network between you and the
  server may be unstable" - a channel-side notice, not a diagnosis. It says
  nothing about which layer; require the monitoring plus Cloud Assistant legs
  before drawing a conclusion.
* "the system is starting, please wait" that never ends - a boot fault, not a
  channel fault. Hand off per
  [handoff-playbook.md](console-channel-diagnosis__handoff-playbook.md); further VNC retries only burn
  the customer's time.
* A screen showing that Windows did not start, after an earlier
  out-of-memory or crash-driven automatic restart - desktop reached the boot
  failure, so the channel is the messenger. Hand off, snapshot-first wording
  applies to any repair.

## Lockout lane

When credentials are refused on every channel while the instance is Running
and monitoring is quiet: check the reset-then-restart ordering first (an
offline reset applies on the next restart only), then suspect an in-guest
login-attempt policy. Neither the lockout state nor the policy behind it is
inspectable from this skill: the guest command set is frozen and does not
include account or audit readers. The customer runs the account-status
commands themselves and pastes the output into `explain`; disk-attach repair
stays a human maintenance action with the snapshot warning in front of it.
