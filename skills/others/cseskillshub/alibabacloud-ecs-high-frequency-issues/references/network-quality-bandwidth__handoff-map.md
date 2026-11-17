# Scope boundaries and handoff routes

This skill owns one vertical: public network capacity, throttling rules, and the attribution of
latency or loss to cloud side, customer local network, or cross-border carrier. Everything else is
routed out, carrying the evidence already gathered. Routing is not a refusal: name the area, show the
readings, and say who handles it.

## Order of work before any handoff

1. read the monitoring numbers and decide the area from the numbers, not from the ticket title. In the
   evidence set, titles saying "bandwidth" turned out to be CPU, memory, disk I/O, or an application
   timeout in a large share of cases;
2. remind the reader that readings taken after an instance hung are unreliable, because the monitoring
   agent exits rather than compete with the workload, so use values from before the incident;
3. hand off with the evidence attached.

## Route table

| Symptom the customer reports | Area | Route | Evidence to attach | Source ticket |
| --- | --- | --- | --- | --- |
| Alarm that disk bandwidth or IOPS reached the specification limit; slow IO | storage performance | `area:resource-bottleneck` | instance id, the alarm text and times, disk ids | `T-8E86B579` |
| Resizing or extending a disk does not show in the guest | storage | `area:disk-expand-diagnosis` | disk id, partition layout from the customer | boundary only, no evidence in this tier |
| Instance will not start, is hung, or both SSH and VNC fail | instance state | `area:instance-state-diagnosis` | instance id, status from `collect`, the readings before the hang | `T-1D60F8DD`, `T-E19652C5` |
| CPU, memory, or IO maxed out while the complaint is "network slow" | compute or storage | same family compute and storage diagnosis; the guest measurement whitelist here is deliberately limited to ping and mtr, so ask for a process listing as the customer's own manual step | the resource readings that disprove the bandwidth story | `T-DD2478F2`, `T-E19652C5` |
| HTTP 499, 502, 504, TLS handshake or certificate problems, web server timeout values, self-hosted VPN tunnel settings, control panel software behaviour | application or third-party software | application operations, or the vendor of that software | the cloud-side readings that exonerate the instance, plus the exact error line | `T-31A262CC`, `T-EB488C8F`, `T-AA85BD7E`, `T-DD2478F2` |
| Confirmed attack traffic, platform security blocking, a request to unblock, WAF or security group rule design | security handling | security response; no skill name is verified for this batch, so say "security handling" rather than inventing one | the blocked target, timestamps, and the traffic evidence | `T-EE77C83A`, `T-88C8B64E`, `T-834EC6FD`, `T-C2BF1C14` |
| Quotation, product selection, coupons, vouchers, refunds, renewal terms | commercial | presales or billing | nothing technical; note the purchase question | `T-F7B7C8A6`, `T-1D3B8E09`, `T-1E659314` |
| CloudMonitor alarm subscription policy, noise reduction, notification blacklist | monitoring configuration, customer side | human action in the console | the alarm identity and the intent | `T-8E86B579` |
| A real hop-by-hop question: which router is dropping, whose link, how to escalate it | link quality | `alibabacloud-mtr-network-diagnosis-customer` | both path tables, timestamps, the customer's local public IP, this skill's cloud-side findings | `T-8AA9D1EE`, `T-2C175432` |
| A load balancer not sending traffic to a backend | LB configuration | human, or the LB area; no verified skill in this batch | backend health check state as the customer sees it, weights | `T-E19652C5` |

## Handoff wording templates

Use the customer's own symptom first, then the finding, then the destination. Never a bare "not our
problem".

- Resource area: "The slowness you see is real, but the numbers point somewhere else. In the window
  `<times>` the CPU was at `<value>`, while outbound bandwidth peaked at `<value>` out of `<purchased>`.
  That is a compute resource question rather than a network one, so I am routing it to
  `<target>` with these readings attached. The network side needs no change."
- Application area: "The instance's CPU, bandwidth, and public reachability all look normal in the
  window `<times>`, with `<readings>`. `499` and `502` are produced by the software layer when the
  client gives up or the backend is slow, so this sits with your web or application configuration.
  What can be ruled out from the cloud side is bandwidth and instance resources."
- Storage area: "The alarm you received is about disk bandwidth and IOPS hitting the limit of the disk
  category, which is a storage performance question, not public network bandwidth. The alarm text and
  the times `<times>` go with it to `<target>`."
- Security area: "The traffic causing the saturation looks like `<pattern>` at `<times>`. Blocking and
  protection rules are handled by `<target>`, and a platform security block cannot be waived by this
  skill. Here is the evidence list to carry over."
- Commercial area: "Pricing and eligibility are decided by billing or presales, and this skill cannot
  quote or commit to terms. What it can confirm is the technical fact behind your question: `<fact>`."
- Link area: "The loss starts at `<hop, address>` at `<times>` and persists to the destination. Deciding
  which link that belongs to, and what can be escalated, is link analysis: routing to `<target>` with
  both path tables."

## Boundary statement for the neighbouring MTR skill

The overlap with `alibabacloud-mtr-network-diagnosis-customer` is real, so keep the split explicit:

| | The MTR skill | This skill |
| --- | --- | --- |
| Main question | which hop on the path is losing or slow, how to take a good bidirectional measurement and read it | what the cloud side actually sold and delivered: bandwidth spec, peak, billing mode, whether it saturated, whether throttling applies, EIP and shared package settings, the specification network baseline |
| On latency and loss | full link probing and judgement | attribution routing only: does a cloud side capacity or throttling cause exist; if not, and the evidence points local or cross-border, conclude and hand over |
| Not done | no capacity or billing conclusions | no promise to repair a cross-border link, and no re-implementation of the tooling guide |
