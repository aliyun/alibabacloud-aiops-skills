# Handoff map: symptoms that are not this tier

This tier owns one question: whether access quality between Chinese mainland networks
and an overseas or China Hong Kong endpoint is degraded, and why. Everything else is
recognised, named, and passed on with the wording below. Do not stretch a cross-border
explanation to cover a symptom that belongs elsewhere; that is the most common way this
class of ticket stalls.

Each row is reachable from the decision tree in
[references/cross-border-link-diagnosis__cross-border-link-diagnosis.md](cross-border-link-diagnosis__cross-border-link-diagnosis.md), section 3.

| Recognition feature | Where it belongs | Wording to send |
|---|---|---|
| Disk resized in the console, but the guest still shows the old size | `area:disk-expand-diagnosis` | A resize that has not taken effect is a partition and file-system adjustment matter; use area:disk-expand-diagnosis. |
| Instance will not start, or is stuck between states | `area:instance-state-diagnosis` | Boot and state-transition faults are outside this tier; use area:instance-state-diagnosis. |
| Slow disk read or write, throughput below the purchased specification | `area:resource-bottleneck` | Storage latency is a different measurement path; use area:resource-bottleneck. |
| Bandwidth fully used with no cross-border segment involved | the advanced-network-diagnostics extension package | A local capacity ceiling with no cross-border factor belongs to the network quality and bandwidth check in the advanced-network-diagnostics extension package. |
| Failure happens at SSH authentication or service configuration, unrelated to the path | `area:ssh-connection` | Credential and service configuration faults belong to area:ssh-connection. |
| Layered unreachability across DNS, the acceleration layer, or the origin application | `area:web-inaccessible-slow` | Site-layer diagnosis belongs to area:web-inaccessible-slow. |
| Internal reachability, or the outbound direction governed by a private network, address translation, or a route table | the advanced-network-diagnostics extension package | Private-network and egress configuration belongs to the intranet egress check in the advanced-network-diagnostics extension package. |
| The blocker is mainland filing or registration requirements rather than link quality | `area:icp-filing-guide` | Filing rules and service codes belong to area:icp-filing-guide. |
| Only the server management panel sign-in or QR scan fails while the site port works | the app-deploy-and-site-build extension package | Panel sign-in behaviour belongs to the panel diagnosis in the app-deploy-and-site-build extension package. |
| Attack traffic and a resulting blackhole are already visible | the security-audit-and-intrusion-response extension package | Attack and blackhole handling belongs to the attack and blackhole diagnosis in the security-audit-and-intrusion-response extension package. |
| After the cross-border path is excluded, one transfer tool or protocol misbehaves | the boot-and-login-repair extension package | Protocol and tool configuration belongs to the file transfer diagnosis in the boot-and-login-repair extension package. |
| The resource is restricted by a platform policy decision | the account-and-service-process extension package | Policy restriction appeals belong to the punishment appeal guide in the account-and-service-process extension package. |
| The request is for a change: cleanup, restart, firewall edit, address swap | human execution | This skill is read-only and will not perform or generate the change; the human runbook and the risk statement are provided instead. |

## Three shapes that need a decision, not a handoff

- **Resource not under this account.** Only resources of the querying account can be
  read here. Ask the owning account to open the request. Do not reason about the other
  account's configuration.
- **Third-party reputation model.** When another platform rates the address as risky,
  state plainly that the cloud side shows nothing abnormal and that the review belongs
  to that platform. A different address may be requested, but the third party decides
  how it rates it.
- **Carrier-side block.** When only certain cities or carriers are affected, the report
  goes to that carrier with address, cities, and timestamps, and an escalation runs in
  parallel. Only a fresh test from the affected city confirms a lifted block, so the
  ticket stays open until that test exists.

## Partial information

If the symptom cannot be pinned to any row and the inputs needed for the geography test
are missing, do not pick a handoff target. Emit `STATUS: DEGRADED` with the missing
items, each stating how to obtain it, and continue from there on the next turn.
