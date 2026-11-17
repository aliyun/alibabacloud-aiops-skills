# Evidence pack: what to collect, and the only links this skill cites

A DDoS, blackhole or penalty case is argued with artefacts, not adjectives. The
report this skill prints is meant to be pasted straight into a ticket, so the
same fields are always collected in the same order, and every external statement
carries its source.

## 1. Case header

| Field | Source |
|---|---|
| Instance id, name, zone, region | `ecs:DescribeInstances` output, echoed with the region actually queried |
| Public IP(s), private IP(s), whether the public address is an EIP | `ecs:DescribeInstances` plus `vpc:DescribeEipAddresses` |
| Instance charge mode, internet charge mode, max outbound bandwidth | `ecs:DescribeInstances` |
| Control-plane state (Running, Stopped, ...) at query time | `ecs:DescribeInstanceStatus` cross-checked with `ecs:DescribeInstances` |
| Attached security groups and the full rule set with priorities | `ecs:DescribeSecurityGroups`, `ecs:DescribeSecurityGroupAttribute` |
| Effective decision per port, in priority order | Printed by this skill from the rules above |
| Whether anyone operated on the instance in the window | `ecs:DescribeInvocations` history (history only, not a live reading) |
| Account the readings belong to | `sts:GetCallerIdentity` provenance tag |
| Incident window and the customer's own words | `--time-window`, `--symptom`, `--alarm-text`, `--error-string` |
| What the customer forbids | `--forbidden-actions`, reprinted at the top of every report |

## 2. Console artefacts the customer must capture

| Artefact | Where | Why it matters |
|---|---|---|
| Blackhole and scrubbing event list for the IP, with the event detail open | DDoS protection console, asset and event pages | The only authoritative statement of state, thresholds and timing. Use a desktop browser: the mobile app does not show all events |
| Traffic evidence package download | Same console, the event detail action | The official proof for a report, an insurer or an appeal |
| Asset protection thresholds for the instance's IP | Same console, asset detail | Replaces any remembered numeric threshold |
| Security Center alarm list and each alarm's detail | Security Center alarm page | Establishes the host-compromise area, or its absence |
| The verbatim SMS or internal message text | The customer's own phone or message centre | Ports, direction and expiry of a platform penalty are only in this text |
| Penalty record list and the release application state | Security management penalty page | Content penalties are only visible and only liftable there |
| Per-instance billing detail for the incident days | Billing console, expense detail by instance | Separates attack egress cost from pay-as-you-go product cost |
| Console one-click diagnostic report for the instance, if already run | ECS instance diagnostics page | Carries network drop and bandwidth items this skill cannot read |

## 3. Guest-side readings (run by the customer, read-only)

Copy the command, run it, paste the output. Nothing here changes state.

Linux:

```
ss -tunap
ss -tunp state established
lsof -nP -i
ps aux --sort=-%cpu
free -m
df -h
uptime
last -n 50
```

Windows (an elevated prompt is not required for these):

```
netstat -ano | findstr :9122
netstat -ano | findstr 7740
tasklist | findstr 7740
```

Web or mail logs, for the incident hour only:

```
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -n 20
```

Record the command, the time it was run, and the raw output. Redact anything
secret before posting. Never include a password, a private key or a panel login
in a ticket, and if one was already sent through another channel, change it
before continuing.

## 4. Appeal evidence for an external block

When a peer site, a messaging platform, a registrar or an anti-spam listing is
the one doing the blocking, the appeal is answered by artefacts from the
customer's side, and Alibaba Cloud can only confirm that its own platform raised
nothing:

* the request log lines showing what the instance actually sent, with user
  agent, target path and timestamps;
* a screenshot of the served directory proving the reported path no longer
  exists, plus a capture showing it now returns 404;
* the outbound connection reading proving no process keeps contacting the peer;
* the instance's egress address at the time, since a shared or changed address
  is the usual reason for a blanket listing;
* for a mail case: the filed domain, the SMTP port in use, and whether the
  destination accepted IPv4 only.

## 5. Links cited by this skill

Console entry points (the `{region}` segment must be replaced with the region
actually queried - the instance's own region, never a remembered default):

* DDoS protection, ECS asset and event pages:
  `https://yundun.console.aliyun.com/?p=ddos#/asset/ecs/{region}`
* Security Center sign-in: `https://yundun.console.aliyun.com/`
* Security Center alarms:
  `https://yundun.console.aliyun.com/?p=sas#/securityAlarm/{region}`
* Security Center full-disk scan:
  `https://yundun.console.aliyun.com/?p=sas#/virusKill/{region}`
* Security Center overview, where the pay-as-you-go switch lives (billing is T+1):
  `https://yundun.console.aliyun.com/?p=sas#/overview/home/{region}`
* Security management, penalty records and the release application:
  `https://yundun.console.aliyun.com/?p=scnew#/sc/event/resources`
* Security groups of the instance's region:
  `https://ecs.console.aliyun.com/securityGroup/region/{region}`
* Per-instance billing detail:
  `https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance`

Documentation:

* Getting started with security groups:
  `https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups`
* Security group guidance and worked examples:
  `https://help.aliyun.com/zh/ecs/user-guide/security-groups-for-different-use-cases`
* Windows instance high-bandwidth investigation and resolution:
  `https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances`
* Configure swap on a Linux instance:
  `https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance`
* ECS security hardening summary: `https://help.aliyun.com/knowledge_list/60787.html`
* Create a snapshot: `https://help.aliyun.com/document_detail/25455.html`
* Create a single snapshot:
  `https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot`
* Roll a disk back from a snapshot:
  `https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot`
* Snapshot billing rules: `https://help.aliyun.com/document_detail/56159.html`
* Snapshot product overview: `https://help.aliyun.com/zh/ecs/product-overview/snapshots-1`
* Delete a snapshot: `https://help.aliyun.com/document_detail/128131.html`
* Security Center 7-day free trial:
  `https://help.aliyun.com/zh/security-center/product-overview/apply-for-a-7-day-free-trial-of-security-center`
* Security Center pay-as-you-go items:
  `https://help.aliyun.com/zh/security-center/product-overview/pay-as-you-go#0ec8ae4c6bn06`
* Change public bandwidth billing: `https://help.aliyun.com/document_detail/99059.html`
* Convert a fixed public IP into an EIP: `https://help.aliyun.com/document_detail/61290.html`
* Unbind an EIP: `https://help.aliyun.com/document_detail/65204.html`
* Purchase and bind an EIP: `https://help.aliyun.com/document_detail/72125.html`
* Shared traffic package purchase: `https://common-buy.aliyun.com/?commodityCode=flowbag`
* Trial-instance usage scenarios: `https://help.aliyun.com/document_detail/2839344.html#2738af3ab7x4e`
* Instance identity and network attributes from inside the guest:
  `https://help.aliyun.com/zh/ecs/user-guide/view-instance-metadata.md`

No other URL may be quoted by this skill. If a needed page is missing above, the
report says the page could not be sourced rather than inventing one.
