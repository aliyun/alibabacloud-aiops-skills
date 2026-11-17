# Handoff Matrix

Out-of-scope symptoms, how to recognize them, and where they go. Recognize,
state the boundary, hand off with evidence. Do not attempt an out-of-scope
diagnosis, and do not stay silent about it - a customer who is never told the
boundary keeps waiting for an answer that will not come.

## Sibling skills

| Symptom | Recognize by | Hand off to |
| --- | --- | --- |
| Load balancer, VPC interconnect, transit router, hybrid cloud link, DNS product behavior, cross-VPC or cross-region design | The question is about network **product** architecture rather than about one instance's reachability | `alibabacloud-network-diagnose` |
| Disk capacity full, inode exhaustion, expansion not taking effect, partition not grown | Complaint mentions space, inodes, a filesystem that did not grow | `area:disk-expand-diagnosis` |
| Disk throughput or latency, slow I/O, high I/O wait | Complaint mentions speed of I/O rather than reachability | `area:resource-bottleneck` |
| Instance will not start, stuck in stopping, unexpected state, unreachable because it is not running | `Status` is not `Running` | `area:instance-state-diagnosis` |

An instance that is not `Running` has no working network path at all. The
diagnosis script reports this immediately and points at the instance-state
skill; resolve the state before investigating reachability.

## Application and service layer

| Symptom | Recognize by | Handling |
| --- | --- | --- |
| HTTP 403 | Status code in the error text, or the customer says the site loads but refuses access | `ATTRIBUTION: application-layer`, `VERDICT: OUT-OF-SCOPE`. The connection reached the instance and the service answered. File permissions, a missing index file, virtual host matching and access rules are application concerns. |
| HTTP 502 or 503 | Status code in the error text | Same. The reverse proxy answered; the upstream service is the question. |
| Connection refused | `refused` error class | Same. The host was reached and nothing accepted that port. Check the service state and its bind address with the customer, then hand to the application owner. |
| Certificate, plugin or API errors from an application | The error names an application component rather than a network primitive | Confirm whether the network path reached its target, then hand off. |

The decisive test for this whole group is **request arrival**: if the customer's
request appears in the service log, the network layer did its job. Say so
explicitly before handing off, because it stops the customer from continuing to
change network configuration.

## Third-party platforms

| Symptom | Recognize by | Handling |
| --- | --- | --- |
| Search-console site verification failing | The customer names a third-party verification flow; a browser can reach the site and see the verification code | Confirm packet arrival in the service log, then hand to the platform's own process. Verification method and file placement are platform concerns. |
| A third-party service cannot reach the customer's server | The failing client is the third party, not the customer | Collect the third party's source address range if published, check the ingress rules against it, then hand off. |
| A closed third-party SaaS is unreachable from a mainland instance | Target is a third-party service the customer does not control | Cross-border branch, with the hard limit that acceleration cannot front a closed third-party SaaS. See `cross-border-and-blockage.md`. |

## Platform-side states with no query entry

| Symptom | Recognize by | Handling |
| --- | --- | --- |
| Anti-DDoS blackhole or cleaning status suspected | Global unreachability from many vantage points; the customer asks whether they have been blocked | Escalate to a support ticket. There is no public query entry point. **Make no claim** about whether a block is in force - the skill cannot see it. |
| Underlying host incident, unexpected restart | The instance restarted without customer action, or a fault notice was received | Escalate with the evidence bundle. |
| Ingress timeouts with every check clean | Ingress direction, timeout class, no cloud-side finding, rules and public address all correct | Escalate with the evidence bundle. Say which checks were already completed so the next round does not repeat them. |

A customer who arrives with their own completed checklist is a gift: forward it
verbatim in the escalation rather than re-running it.

## Customer-side environment

| Symptom | Recognize by | Handling |
| --- | --- | --- |
| A name resolves to loopback or to a wrong address on the customer's own machine | The customer's local resolution differs from the authoritative record | Provide the self-check list and stop. The client machine is not under management here. |
| Local DNS cache, browser cache, an extension, a corporate proxy on the client side | The service answers normally from other vantage points | Same. Ask for a retry from another network or device - that single comparison settles it. |
| Customer premises equipment, a private data center, another provider, an office network | D1 found no matching instance in this account | `ATTRIBUTION: ownership`. State that the asset is not an ECS instance of this account, and hand to the customer's own network and host-firewall checks. |

Self-check list to provide: the local hosts file; the local DNS cache; the
browser cache and any extension; the local proxy configuration; a retry from
another network, another device or another province; and the exact error text
with the address bar visible.

## Change requests

These are console decisions owned by the resource holder. This skill explains
applicability, gives the documentation entry point, states the risk, and
**executes nothing**.

| Request | Handling |
| --- | --- |
| Add, change or remove a security group rule | Point at the console path. State that a rule takes effect once added and there is no propagation delay. |
| Change a network ACL, a route table, a default route, an SNAT entry | Same. |
| Change a public IP address, convert a fixed public address to an EIP, associate or disassociate an EIP | Explain the constraints, which must be checked in the console: some instances cannot have the address changed directly after a short window following creation, and promotional pricing may not survive a configuration change. State that the operation may be irreversible and may carry billing consequences or a price difference. |
| Change bandwidth, buy an acceleration product, buy an EIP | Explain applicability only. **Do not estimate cost.** Billing is the customer's assessment against the current catalog. |
| Permit ICMP so path measurement tools work | Explain that this is a security-relevant change the resource holder makes deliberately. |
| Restart an instance or a network service, kill a process | Never. Explain the console path and the impact. |
| Delete a snapshot, unsubscribe, downgrade | Never. These carry billing consequences and are outside this skill entirely. |

Risk wording to reuse: the operation may be irreversible; charges and any price
difference are determined by the console at the time of the change, not by this
skill; promotional or activity pricing may not survive a configuration change.

## Escalation bundle

Whatever the destination, hand over the same bundle so the next round starts
informed:

- Instance identity, region and region class, state, addresses, security groups
  and their types.
- The probe: direction, target, resolved target location and how it was
  determined, port, protocol, client address and location if supplied.
- The error class and the customer's verbatim error text.
- Every security group rule that matched or was a candidate, quoted as read
  back, with its priority.
- The VPC path: VSwitch CIDRs, route tables, NAT gateways, SNAT coverage.
- Any guest-side evidence already collected, as pasted text.
- The degradation log, naming every query that failed and what its absence
  prevents concluding.
- Disagreements between platform-side and customer observation, unresolved and
  labelled as such.

## Boundary wording

Keep it short, factual and non-defensive. Name what was verified, name what lies
outside, name the destination, and attach the bundle. Do not apologize for the
boundary and do not speculate about the destination's findings - the next owner
has evidence this skill does not.
