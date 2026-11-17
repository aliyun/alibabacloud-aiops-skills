# Cross-border and third-party link cases

This is the area where a support ticket most often ends without a fix, and where an assistant does
real damage by implying that a fix exists. Read the whole page before answering one of these.

## When this page applies

- the instance is in mainland China and the destination is outside, or the reverse;
- ICMP to the foreign destination is 100 percent lost while a domestic destination is fine;
- TCP 443 is reset while 80 works, or the TLS handshake fails on some resolved addresses of the same
  domain and succeeds on others;
- a path test shows sustained loss starting at a carrier backbone or international egress hop.

## Split the evidence into three parts and never merge them

| Part | What it shows | How this skill obtains it |
| --- | --- | --- |
| Cloud side | the instance itself is not capacity limited and is reachable | `collect` plus `judge`: billing mode, configured peak, readings over the stated window |
| Peer side | whether the destination answers at all, and from where | the reverse measurement printed by `guide`, run by a human and pasted back, plus per-address tests and the customer's own result from another network; all of it is customer-supplied evidence |
| Transit segment | where on the path between them the loss starts | the bidirectional path tables, interpreted with [mtr-interpretation.md](network-quality-bandwidth__mtr-interpretation.md) |

The failure mode to avoid is answering "the server is fine" when the customer asked about a specific
destination. State all three, then say which one carries the fault. In the evidence set, one ticket
listed four concrete checks (security group, cloud firewall, anti-DDoS cleaning, SYN protection, which
side sent the reset, why the target ignored probes) and none of them were addressed; the run then
closed without a conclusion. If the customer lists checks, answer each one as done, impossible here,
or handed over. Never leave a listed check silently unanswered.

## What this skill can establish on its own

- the cloud side is clean, with numbers and a window, so the customer stops suspecting their purchase;
- the loss is reproducible toward one destination and absent toward another in the same region, which
  localizes the problem to the path or the peer;
- per-address behaviour differs within one domain's DNS answers, which points at a specific transit
  route rather than at the service;
- TCP probe loss coexists with successful application requests, which means the probe is not the
  measurement to trust (see rule 3 of [mtr-interpretation.md](network-quality-bandwidth__mtr-interpretation.md)).

## What to say, and what never to say

Say, in this order:

1. the finding, with the readings that support it;
2. the boundary, verbatim in substance: Alibaba Cloud administers the data center network, and has no
   operational authority over the international carrier segment, so it cannot adjust or repair that
   segment;
3. why routes differ: "different destination addresses take different paths, and each region reaches a
   different set of carrier exits, which is why one service is slow and another is fine, and why
   another provider can look better for one destination";
4. the options that exist, as products the customer buys and configures themselves:
   - a premium multi-line BGP EIP, documented for lower latency access to services in mainland China;
   - Global Acceleration, which routes the traffic over the provider backbone instead of the public
     carrier path;
5. the mitigation that costs nothing when the loss is load dependent: schedule bulk transfers outside
   the congested hours;
6. the honest limit: for a given public path there may be no better answer today, and a change of
   region or IP address is not available on a purchased instance.

Never say or imply:

- "we will fix the link", "we will ask the carrier to repair it", or a promised improvement percentage;
- a numeric latency or availability guarantee for a corridor, a region pair, or a product;
- "your instance is the problem", when the cloud side readings are clean;
- "changing region or IP will solve it": the region of a purchased instance cannot be changed, and a
  new public IP means repurchasing, which can cost the customer a promotional price.

Documentation to attach to the answer:

- premium BGP EIP for lower latency access:
  https://help.aliyun.com/zh/eip/use-cases/use-bgp-pro-eips-to-access-web-services-with-low-network-latency
- Global Acceleration scenarios: https://help.aliyun.com/zh/ga/product-overview/scenarios
- Global Acceleration concepts: https://help.aliyun.com/zh/ga/product-overview/terms
- path testing with MTR: https://help.aliyun.com/zh/ecs/user-guide/use-mtr-tool-for-network-analysis

## Handoff

- Hop-by-hop fault localization, or a conversation about a specific carrier segment:
  `alibabacloud-mtr-network-diagnosis-customer`, carrying both path tables and the timestamps.
- Peer refuses connections, or a certificate or protocol problem at the destination: the peer's
  operator, and the customer coordinating a capture on their side. This skill does not configure a
  customer's application, VPN tunnel, or TLS stack.
- A case that needs a bidirectional packet capture to settle: give the capture as a manual step with
  the exact scope, then close what the cloud side can already prove. This skill never runs a capture
  at all; see [guest-command-whitelist.md](network-quality-bandwidth__guest-command-whitelist.md).
- A purchase decision between premium EIP, Global Acceleration, or another region: presales. This
  skill can state the mechanism, not the commercial terms, and never predicts the improvement.

## Expected output shape

```
Cloud side: <peak, billing mode, readings, window> -> <clean | at limit>
Peer side:  <what answered, what did not, from where>
Transit:    <first sustained loss hop and address> -> <owner>
Boundary:   Alibaba Cloud manages the data center network only; no authority over the international segment.
Options:    <premium BGP EIP | Global Acceleration | off-peak scheduling>, all customer configured
Confidence: <high | medium | low> and what it rests on
STATUS:     DEGRADED unless the cloud side alone explains the symptom
```

The default status on this area is `DEGRADED`, because the failing segment is outside what the cloud
can measure or change. Reaching `OK` here requires a cloud-side cause that was actually demonstrated.
