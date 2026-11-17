# Bandwidth, billing, and throttling facts

Facts used to answer "is it throttled, and why". Each row states the fact, how to say it to the
customer, and where it came from. Ticket identifiers are Alibaba Cloud ticket numbers from the
evidence set behind this skill. Anything without a source is listed under "do not assert".

## Speed and unit conversions

| Fact | Say it this way | Evidence |
| --- | --- | --- |
| Bandwidth is sold in Mbps (megabits per second); transfers are felt in bytes per second. 1 Mbps is about 128 KB/s | "The instance was purchased at 1 Mbps, which is about 128 KB/s, so a 20 MB upload will be very slow or will time out. That is the specification limit, not a fault." | ticket `T-43B270A7` |
| 1 MB/s equals 8 Mbps | convert before comparing a download manager figure with the purchased peak | arithmetic |
| Peak speed is what is capped; a single TCP connection often cannot saturate it | a single-threaded download reaching only part of the peak is expected; suggest a multi-connection tool such as aria2 before calling it a fault | ticket `T-A6A39284` |

## What limits the effective outbound rate

State it as one layered formula so the answer never contradicts itself:

```
effective outbound ceiling = min(
    configured peak of the instance public bandwidth or of each EIP,
    instance specification network capability (documented per instance family),
    billing mode ceiling,
    platform ceiling)
```

Only the first term is machine readable through the APIs this skill calls. The second must be looked
up in the instance family documentation. The third and fourth are rules below. Never quote a single
number as "the maximum" without saying which term produced it.

| Fact | Detail | Evidence |
| --- | --- | --- |
| Several EIPs bound to one instance do not simply add up | each EIP keeps its own configured peak, and the instance specification network capability also applies; a multi-EIP setup normally needs elastic network interfaces attached to the same instance | ticket `T-9BA2AEE7` |
| Multiple EIPs on one instance each limited separately | with two EIPs configured at 100 Mbps and 200 Mbps, each address is served at its own configured peak | ticket `T-9BA2AEE7` |
| Pay-by-traffic billing caps the outbound direction only | inbound traffic is not charged; the outbound peak is the control that limits cost | ticket `T-805AECB0` |
| Pay-by-traffic allows a peak to be configured, up to 100 Mbit/s for one instance | the peak is an upper bound, not a committed service level | ticket `T-592D0E37` |
| No total traffic quota can be configured | "Setting a monthly cap of 30 GB is not supported. Cost follows actual outbound GB, so the only pre-configured control is the bandwidth peak." | ticket `T-592D0E37` |
| Fixed bandwidth billing has no traffic allowance to run out | "Fixed bandwidth limits the peak rate; there is no traffic quota that can be exceeded." | ticket `T-F7B7C8A6` |
| An overdue account throttles the outbound bandwidth of pay-by-traffic instances | symptoms are timeouts and very slow transfers while the instance itself looks healthy; the remedy is to settle the balance, which this skill never does | ticket `T-AA85BD7E` |
| Inbound peak is not adjustable in the same way as outbound, and at low load the inbound rate can exceed the nominal figure | low confidence wording, see "do not assert" | ticket `T-FCCA0D74` |
| A temporary bandwidth upgrade must be verified by comparing readings around the change timestamp | if the measured rate never approaches the new peak, ask whether the change took effect before concluding the upgrade failed | ticket `T-834EC6FD` |

## Monitoring and historical data

| Fact | Detail | Evidence |
| --- | --- | --- |
| Ping latency does not measure bandwidth | "ping only tests small ICMP packets; a web page transfers a lot of HTTP data and is limited by the bandwidth, so a fast ping can still sit behind a saturated link." | ticket `T-80CDD4FF` |
| Historical traffic cannot be attributed to an application, a port, or a peer | the cloud side keeps aggregate bandwidth history only; naming the process requires a real-time look inside the guest at the moment the rate is high, and ongoing fine-grained tracking needs Network Intelligent Service | tickets `T-805AECB0`, `T-91E97892`, `T-43B270A7` |
| Monitoring values taken after an instance hung are unreliable | the CloudMonitor agent exits so it does not compete with the workload; read the values from before the incident | ticket `T-E19652C5` |
| A saturation verdict must carry reading, threshold, and window | "bandwidth was saturated from 21:17 to 21:28 and has since dropped" is a usable statement; "it was running full" is not | tickets `T-43B270A7`, `T-A6A39284` |
| No DDoS event does not mean no abnormal traffic | connection or request spikes can exhaust bandwidth and connections without triggering any anti-DDoS event | ticket `T-9E911AC6` family, `T-EE77C83A` |
| Bill totals arrive late | the final monthly bill is issued at 12:00 on the 3rd of the following month; bill detail lags consumption by 24 hours, and instance-related fields (configuration, spec, nickname, resource group, public and private IP, zone) lag by 48 hours | ticket `T-91E97892` |

## Products and boundaries that come up in these conversations

| Fact | Detail | Evidence |
| --- | --- | --- |
| Alibaba Cloud administers the data center network only | it has no policy authority over cross-border carrier links, so no fix can be promised on that segment | ticket `T-7253A49F` |
| Different destinations route differently | "why is another cloud fine" is answered by the routing path per destination IP, not by a capacity comparison | ticket `T-8AA9D1EE` |
| The region of an instance cannot be changed, and changing the public IP means repurchasing | on promotional instances that can create a cost loss, so it is a presales question | ticket `T-C1573D4E` |
| Security groups cannot block by region | only address and CIDR based rules; geographic blocking needs another product | ticket `T-DD2478F2` |
| To decide whether an IP belongs to a CDN or origin fetch service, first check where the domain resolves | if the domain resolves straight to the instance, the visiting IPs cannot be CDN or origin fetch addresses | ticket `T-C2BF1C14` |
| A self-hosted VPN interface MTU can explain "small packets pass, large packets fail" | in one ticket the customer's own interface dump showed a tunnel MTU of 100, which alone explains an 80 byte success and a 200 byte loss; do not attribute such a case to arrears throttling without checking both | ticket `T-AA85BD7E` |
| Burst capability of burstable instance families concerns the compute baseline | it is not a public bandwidth booster; keep the two ideas apart | documentation `monitor-burstable-instances.md` |

## Sources

Public documentation used for the rules above:

- ECS public bandwidth and throttling: https://help.aliyun.com/zh/ecs/user-guide/network-bandwidth.md
- Public bandwidth billing: https://help.aliyun.com/zh/ecs/public-bandwidth and
  https://help.aliyun.com/document_detail/25411.html
- Converting the billing mode of a fixed public IP: https://help.aliyun.com/document_detail/178883.html
- Linux network traffic load investigation:
  https://help.aliyun.com/zh/ecs/support/query-and-case-analysis-of-linux-network-traffic-load
- Windows instance high bandwidth troubleshooting:
  https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances
- MTR based analysis: https://help.aliyun.com/zh/ecs/user-guide/use-mtr-tool-for-network-analysis
- Network Intelligent Service: https://help.aliyun.com/document_detail/338338.html
- Burstable instance monitoring: https://help.aliyun.com/zh/ecs/user-guide/monitor-burstable-instances.md
- Instance specification and family documentation:
  https://help.aliyun.com/zh/ecs/user-guide/instance-specification-naming-and-classification and
  https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families

Ticket quotes in the tables come from the evidence set used to build this skill. Chinese-language
tickets are summarized in English here; the ticket number is the anchor if the original wording is
needed.

## Do not assert

Mark these as unverified whenever they come up, and offer the customer the documentation or a
human handoff instead of a number.

| Tempting claim | Why it stays out |
| --- | --- |
| "The inbound cap is exactly X Mbps on your plan" | no citable source; the only evidence is a support engineer saying inbound is not adjustable while it can exceed the nominal value at low load |
| "CloudMonitor shows bandwidth as metric `Y`" | the namespace and metric identifiers for this tier were never verified; `collect` only queries them when the operator supplies them |
| "You get 20 GB or 200 GB of free CDT traffic" | the figures were stated in a ticket, but no source in this run confirms them, and they belong to billing anyway |
| "Throttling drops large packets first because of Z" | the mechanism behind the arrears throttling versus packet size story was never closed out |
| "These IPs are CDN origin addresses" | needs the authoritative address range list, which was not available |
| "Your bill will be N yuan" | no billing API is used here; direct the customer to the billing center |
| Any OpenAPI error code for a bandwidth problem | none is verified for this tier; quote request ids from real responses instead |
