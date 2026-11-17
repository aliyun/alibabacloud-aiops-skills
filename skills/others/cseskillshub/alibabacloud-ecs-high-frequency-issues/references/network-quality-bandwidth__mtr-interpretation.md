# Bidirectional path test: request wording and loss interpretation

Scope discipline first. This skill uses a path test only to decide **which side owns** latency or
loss: the customer's own network, the carrier or cross-border segment, or the cloud side. Deciding
which router on the path is broken, and arguing with a carrier about it, belongs to
`alibabacloud-mtr-network-diagnosis-customer`. Hand that over as soon as the question becomes
"which hop is at fault" rather than "whose problem is this".

## What to ask for, in one message

Asking piecemeal is what makes these tickets loop. Request all four at once:

1. the customer's own public IP as seen from their side (for example from any "what is my IP" page);
2. the path from the customer to the instance public IP;
3. the path from the instance back to that customer public IP;
4. the moment each test was run, to the minute.

Item 3 is the command that `guide` prints, so it does not have to be improvised: this skill executes
nothing inside the guest, and the table comes back only when someone runs that printed line and pastes
it. Item 2 has to come from the customer; the skill cannot see their side.

Command wording to give the customer:

- Windows: `WinMTR`, target set to the instance public IP, then copy or screenshot the table after
  about 50 cycles.
- Linux or macOS: `mtr -r -n -c 50 <instance-public-ip>` and paste the whole table.
- Server side, printed by `guide` for a human to run: `mtr -r -n -c 30 <customer-public-ip>`, or with
  `--tcp -P 443` when the symptom is port specific.

## Reading the table

Columns that matter: `Loss%` per hop, `Sent`/`Recv` counts, `Avg` and `Wrst` latency, `StDev`.

### Rule 1: attribute at the first hop that keeps losing

A hop explains the end-to-end result only when it loses continuously **and its successors keep
losing down to the destination**. Loss that appears at one hop and disappears downstream is not the
customer's problem; loss that starts at hop N and persists to the destination is.

### Rule 2: a middle hop that recovers downstream is ICMP rate limiting

Routers often deprioritize the ICMP used by these tests. In the evidence set, one hop reported 96
percent loss while the very next hop reported 3 percent, and the destination itself was clean. That
pattern means the router is limiting ICMP replies, not dropping the customer's traffic. Never tell a
customer "hop 4 is broken" from a single high middle hop.

Practical form of the judgement: the loss that matters is at the destination row, or at a row whose
successors stay at least as bad.

### Rule 3: TCP probe loss is not application loss

A TCP mode path test can be rate limited or reset by middleboxes while the real connection is fine.
In the evidence set, a control test on another instance in the same region showed TCP loss while
twenty curl attempts per batch failed to reproduce any timeout, and the support conclusion was
explicitly that TCP probe loss does not by itself prove the access is broken.

So: only report TCP probe loss as relevant when the application symptom reproduces in the same
window. If it does not, say so plainly and stop there.

## Mapping the first sustained loss to an owner

| Where the sustained loss starts | Owner | What this skill says |
| --- | --- | --- |
| The customer's own gateway or private range (10/8, 172.16/12, 192.168/16) | customer local network | "The loss starts at your own gateway. Reconnect over a different uplink, for example a mobile hotspot, and compare." |
| The first ISP hop after the customer, persisting downstream | carrier access network | "This is on the access path in front of the instance. Retest from another uplink and, if it persists, the carrier is the party to ask." |
| An international egress style hop, for example an address in a carrier backbone range | cross-border carrier link | go to [cross-border.md](network-quality-bandwidth__cross-border.md); no fix is promised |
| The instance's own egress, or cloud side resources are at the same time saturated | cloud side, bandwidth area | stay in this skill and continue with `judge` |
| Only the destination row, while every intermediate hop is clean | the peer or its protection | "The path to it is clean; the far end is not answering. Check whether the service or its firewall is limiting probes." |

Hop ownership inference is a judgement, not a lookup: geographic and ownership data for intermediate
addresses was not available to verify in this run. Report an owner as a hypothesis with the address
that supports it, and never name a specific carrier as fact from an address pattern alone.

## Packet size sweep as an adjunct

When the customer reports that some transfers work and others do not, a size sweep separates the
candidates: `guide --tool ping --packet-size 80,200,1400` prints one command per size. Have them run
one at a time and keep the outputs separate, so the size at which transfers start failing stays
visible. A threshold that sits at a small size points at an interface MTU inside the guest or a
tunnel, not at bandwidth; check the arrears state as well before naming one cause. See
[bandwidth-facts.md](network-quality-bandwidth__bandwidth-facts.md) for the MTU story and [guest-command-whitelist.md](network-quality-bandwidth__guest-command-whitelist.md)
for what may be suggested to the customer.

## What belongs in the report

- both raw tables, or the pasted customer output, with the time each was taken;
- the first sustained loss hop, its address, and its loss and latency figures;
- the successor rows that prove persistence or recovery;
- the owner conclusion with a confidence level, since local side evidence is customer provided;
- if the conclusion is "needs hop-by-hop work", the handoff line with the collected tables attached.
