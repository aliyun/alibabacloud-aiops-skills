# Boundary and handoff matrix

This tier is narrow: public bandwidth value, bandwidth billing mode, temporary bandwidth upgrade,
and the fixed-public-IP-to-EIP path. Everything that merely *looks* like a bandwidth problem is
detected here and handed off, carrying the facts this skill already verified.

A handoff without the verified facts is a failure: the customer has to describe the problem again.
Always attach the live bandwidth value, the bandwidth billing mode, the public address shape, and
whether the peak reached the ceiling.

## Detection table

| Customer wording or reading | What it really is | Action |
| --- | --- | --- |
| "I lowered the config and nothing changed", about CPU or memory | specification change activation | explain the restart requirement, then hand the specification area to the instance configuration tier |
| "disk full", "cannot write", "inode", "partition smaller than the disk", "extend the volume" | block or filesystem capacity | hand off; not a bandwidth question at any point |
| "the OS still shows the old disk size after I expanded it", "extend the volume", "partition not grown" | partition or filesystem growth after a disk expansion | hand off |
| "disk is slow", "IO hangs", "performance below the spec" | block storage performance | hand off |
| "instance stuck starting", "cannot stop", "reboot loop" | instance power state | hand off; never attempt a power action from here |
| "ping times out", "packet loss", "cross-border access is bad", while the monitoring peak is far below the configured bandwidth | link quality, and ICMP may be rate-limited independently | hand off, with the two numbers attached |
| "what will this cost me in total", "bundle a renewal with a discount", "restore my campaign price" | commercial pricing | route to a commercial follow-up; state no figure |
| "which instance type should I buy", "no overseas option on the campaign page" | pre-sales selection | route to pre-sales or commercial |
| "paid the order but the bandwidth still shows the old value" | order processing, once the live value is confirmed different | this tier's own escalation path, see below |

## Handoff targets

The names below come from the batch template and have **not** been checked against the live skill
registry. Confirm before quoting one to a customer; if the target skill is not available, the
correct behaviour is to say which area the problem belongs to and to escalate a ticket instead.
See [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).

| Area | Candidate skill name | Status |
| --- | --- | --- |
| disk capacity and inode | not named in this tier's inputs | verify, else ticket |
| disk expansion not visible in the OS | `area:disk-expand-diagnosis` | unverified name |
| instance boot and shutdown state | `area:instance-state-diagnosis` | unverified name |
| disk IO performance | `area:resource-bottleneck` | unverified name |
| general instance inspection | `alibabacloud-ecs-health-inspection` | exists online, low overlap with this tier |

## Ready-to-send wording

Replace every brace with a value the script printed. Do not invent one.

**Link quality handoff.**
"Your instance currently has {internet_max_bandwidth_out_mbitps} Mbit/s of outbound bandwidth on
{bandwidth_internet_charge_type}. The monitoring figure you provided for {window} is {peak}, which
is below that ceiling, so the symptom is not a bandwidth shortage. Packet loss on a cross-border
path, and especially loss that shows only in ping, is usually the link or ICMP being rate-limited;
testing the real TCP port is what tells them apart. This belongs to link-quality troubleshooting
rather than to this skill, so I am passing it on together with the figures above. Global
acceleration and cloud interconnect are the products that address cross-border quality."

**Specification change handoff.**
"The bandwidth side is already correct: {internet_max_bandwidth_out_mbitps} Mbit/s, no restart
needed for that part. What you describe is a compute specification change, and a specification
change only takes effect after the instance restarts. Before restarting, choose an off-peak window,
stop the application so buffered writes reach the disk, and take a snapshot; snapshots are billable.
I am handing the specification side to the matching skill with the values above."

**Capacity or disk handoff.**
"What you are describing is disk capacity inside the filesystem rather than public bandwidth. For
the record, the bandwidth side is {internet_max_bandwidth_out_mbitps} Mbit/s on
{bandwidth_internet_charge_type} and the address is {public_ip}. I am routing this to disk capacity
troubleshooting and attaching those facts so you do not have to restate them."

**Commercial handoff.**
"Total price for a combined renewal with a bandwidth change depends on the pricing attached to your
account, which is not visible to me and which no agent can compute reliably from here. I am passing
this to a commercial colleague, who will contact you by phone; the usual expectation is one
business day. In the meantime, the price configurator gives a list-price estimate for a new
purchase, and the change page shows an estimated amount before you confirm anything."

## Escalating from within this tier

For "paid but not effective", after the live value has been read and still differs from the
ordered value, open a ticket containing exactly:

1. order id, instance id and region;
2. the ordered value and the live value the script printed;
3. the time of the order and how long the customer has waited;
4. whether a public IP was expected to change as well, because that is the EIP path and not a
   bandwidth side effect;
5. the session id from the report header, so the same reads can be reproduced.

Do not tell the customer to repeat the purchase to fix a synchronisation problem, and do not accept
"clear your browser cache" as an answer to a configuration value that the API confirms is wrong.
