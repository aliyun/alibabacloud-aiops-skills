# Handoff map

This skill owns one area: the address as an asset (type, ownership, binding,
conversion rules, billing caliber). Everything that looks like "the address is
wrong" but is really about a path, a policy, or a commercial action is recognized
here and passed on, with the evidence that excludes the asset area.

## Where the line sits against the neighbouring public-network skill

| | This skill | `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` |
| --- | --- | --- |
| Question | is the address the right type, in the right place, at what cost to change | does a packet get there and back |
| Evidence | instance state, address type, EIP status and binding | path, route, packet behaviour, service response |
| Typical opening | "change my public IP", "can I keep this address" | "ping fails", "connection times out" |

Hand over with the asset-side result already computed: "the address is assigned and
bound, so this is not an ownership or binding problem".

## Recognition table

The same table is embedded in `scripts/areas/public_ip_guide/_constants.py` as `HANDOFF_RULES`, which
`--intent triage` scores against `--symptom`.

| Recognised by | Area | Handoff to |
| --- | --- | --- |
| reset on 443, domain only works over the address, mainland region, unregistered domain | filing interception | `area:icp-filing-guide` |
| ping fails, packet loss, handshake with no data, timeouts, route or return path | public path | `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` |
| throughput, latency, cross-region or international link quality | link quality | `area:network-quality-bandwidth` |
| port closed, connection refused, service not listening, firewall or security group | service exposure | `area:access-block-layered` |
| SSH or Workbench failure | secure shell | `area:ssh-connection` |
| RDP, mstsc, remote desktop, one client tool only | windows remote | `area:windows-rdp` |
| DDoS, attack traffic, blackhole, mitigation | attack handling | `area:attack-blackhole-diagnosis` |
| overdue, arrears, stopped for non-payment | arrears | `area:arrears-trial-billing-stop` |
| expiry, retention window, release protection, about to be released | expiry and retention | `area:expiry-release-retention` |
| refund, invoice, coupon, cancellation | commerce | `area:unsubscribe-refund` |
| the transfer procedure itself, not the address question | account transfer | `the Alibaba Cloud account ownership transfer process (console ticket; no skill here performs it)` |
| changing the spec, the image, or the CPU architecture | instance change | `area:instance-modify-diagnosis` |
| raising or lowering bandwidth with no address question in it | bandwidth change | `area:bandwidth-modify-guide` |

## Wording that closes the loop

Each handoff says three things, in this order: what was ruled out here, where the
symptom belongs, and what must not be tried.

- Filing: "the address is assigned and bound, so this is not an address problem; it
  looks like filing interception on a mainland region, which needs the filing flow.
  Do not try to fix it by changing the address: it will not take effect, and the EIP
  conversion cannot be undone."
- Path: "the address is correctly assigned, so the fault is on the path; that goes to
  the public network troubleshooting skill. Changing the address will not repair a
  path."
- Client: "the instance answers on one route and not on this client, so the client or
  protocol is the question, not the address."
- Attack: "a new address leaks again and does not stop the attack; mitigation is a
  separate capability. This skill only answers whether a change is possible and what
  it costs."
- Lifecycle or money: "the release timeline, the settlement, and the refund belong to
  the corresponding flow; the address rule here is only that a released address can be
  reclaimed inside 7 days by the customer, and only while no other account holds it."

## The sentence that must survive every handoff

A recorded customer ran the whole irreversible conversion path, on their own, to fix
what turned out to be filing interception. The gate exists so that the next customer
is told this before spending the change:

> Changing the address does not fix this, the conversion cannot be undone, and it will
> add its own fees.
