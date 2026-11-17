# Security group and authorization-object checks

The security group is the first place an SSH establishment failure is decided, and
also the place where a correct-looking rule can be permanently ineffective. This
page is the reasoning layer used by phase S3 in
[decision-tree.md](ssh-connection__decision-tree.md).

## What is checked

`ecs:DescribeSecurityGroupAttribute` is called with `Direction=ingress` for every
group attached to the instance. A rule is relevant when all of these hold:

| Field | Requirement |
| --- | --- |
| `Policy` | `Accept` |
| `Direction` | `ingress` |
| `IpProtocol` | `tcp`, or a protocol that covers everything |
| `PortRange` | covers the port under test: `22/22` covers 22, `0/65535` covers every TCP port, and the `-1/-1` sentinel means "any port" and is honoured only on a rule whose protocol is not TCP-specific |
| `SourceCidrIp` / `Ipv6SourceCidrIp` | the authorization object examined below |

A `Drop` rule with a better `Priority` value wins over an `Accept` rule, so a
customer who added a deny entry first will see a timeout no matter how many allow
entries follow.

## Reading the outcome

| Situation | Conclusion | Who fixes it |
| --- | --- | --- |
| No Accept rule covers the port | The port is closed at the network boundary. `Connection timed out` when packets are dropped, `Connection refused` when they are rejected. This is very often a rule the customer deleted while hardening the group. | A human adds the rule in the console: `https://ecs.console.aliyun.com/securityGroup/region/<region-id>#/` |
| Accept rule, authorization object `0.0.0.0/0` | The port is reachable, and also exposed. Report it separately from the connection question: an SSH port open to the whole Internet is brute-forced, which is how accounts get locked and how a later "permission denied with the right password" complaint is produced. Recommend narrowing to specific addresses. | A human |
| Accept rule whose object is not a public unicast address | **The rule can never match.** See the next section. | A human, after the customer re-reads their address |
| Accept rule whose object is a public CIDR, and the customer's egress address is inside it | Network layer cleared for this instance; move on to the guest and the customer-side path. | - |
| Accept rule whose object is a public CIDR that does not contain the customer's egress address | The packet is dropped before the instance. Egress addresses rotate on mobile and corporate networks, so the reading must be taken at the moment of failure. | A human |
| Nothing supplied for the egress address | Report the object and mark the gap; a match cannot be asserted either way. | Customer reads their address |

## Private, NAT and internal objects

An authorization object only works if it is the address the server actually sees.
These ranges are not:

| Range | Where it comes from | Why the rule is dead |
| --- | --- | --- |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | The laptop's own interface address | The carrier or office gateway translates it before it leaves the network |
| `100.64.0.0/10` | Carrier-grade NAT pools, and overlay networks such as Tailscale | Never appears as the source address at the instance edge |
| `100.100.0.0/16` and other Alibaba Cloud internal service ranges | In-instance metadata and internal services | Internal to the platform, not to the customer's traffic |
| `127.0.0.0/8`, `169.254.0.0/16`, `224.0.0.0/4`, `240.0.0.0/4` | Loopback, link-local, multicast, reserved | Not routable source addresses |
| IPv6 unique-local `fc00::/7` and link-local `fe80::/10` | Local or overlay addressing | Same translation problem as the IPv4 private ranges |

This exact mistake produces the ticket pattern "I added my IP to the whitelist and
it still times out", and the misleading companion pattern "editing the security
group fixed it", which is a coincidence: touching the group re-applies the rules,
and a retry then succeeds because the customer's own egress address had meanwhile
changed back.

## Getting the customer's real egress address

Ask for it from a public echo service opened in a browser - `https://ip.cn/`,
`https://myip.ipip.net` or `https://cip.cc/` all answer the question - and insist on
the IPv4 shown there, not on what the operating system reports about its network
interface. If the reported value falls into any range above, the customer is reading
their private address and the check has to be repeated.

## Console and Workbench source addresses

Connections made through the web console reach the instance from Alibaba Cloud
source ranges, not from the customer's laptop. Those ranges are published in the
Workbench documentation, and conversations have quoted them inconsistently (both a
`/14` and a `/16` under the same `100.104` prefix, plus various public `/24` and
`/26` ranges for the browser path).

**Do not hardcode a source range in advice or in a rule.** Look it up in the current
documentation first:

* Workbench overview:
  `https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md`
* Connecting to a Linux instance with a password or a key:
  `https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-or-key.md`
* Security group quick start:
  `https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md`

If a customer connects through the console and reports failure, the console source
range must be allowed; if they connect from their own terminal, a console source
range in the rule is proof that nothing allows them. The `--client-tool` input is
what distinguishes the two, so always ask how they connect.

## Boundary

Reading rules uses a describe action and is safe. Adding, editing, removing or
reordering a rule changes the instance's exposure and is always performed by a human
in the console. The skill states the exact rule needed and stops there.
