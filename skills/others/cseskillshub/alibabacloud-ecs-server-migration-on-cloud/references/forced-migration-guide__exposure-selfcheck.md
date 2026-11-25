# Exposure and attribution self-check: breaches, traffic, and blame disputes

Scope: the customer reports high egress traffic, brute-force attempts, scraping, or a service
failure and attributes it to the platform, while the read-only cloud facts show no platform
fault. Related: [incident and SLA](incident-sla-guide.md), [fees and refunds](billing-dispute-guide.md),
[hand-off boundaries](handoff-boundaries.md).

## What this skill reads, and what it must not pretend

`DescribeInstances` reports, per instance, the SECURITY GROUPS it is bound to. That binding is
the anchor for an exposure self-check. The skill does not open, read, or change those rules, does
not log into the instance, does not run anything inside it, and cannot see historical traffic or
historical per-process data (the platform does not retain it). Anything needing in-guest readings
is a command the CUSTOMER runs and pastes back.

## Port-exposure self-check (console, read first)

- Are the remote ports open too broadly? For Linux, port 22; for Windows remote desktop, port
  3389. If the source is `0.0.0.0/0`, narrow it to your office or VPN CIDR.
- As an immediate stop-loss, block the specific abusive source IP in the security group.
- Turn on an automatic snapshot policy as a data safety net. Note: snapshots incur storage cost.
  Doc: https://help.aliyun.com/zh/ecs/user-guide/create-an-automatic-snapshot-policy-1

## In-guest READ-ONLY self-check (customer runs and pastes the output)

Linux:
- `top`            shows which process is consuming CPU right now (cannot replay history).
- `cat /etc/resolv.conf`   check the name servers. If public DNS is configured and is causing
  unexpected outbound lookups/traffic, the customer can switch to the internal VPC resolvers
  `100.100.2.136` and `100.100.2.138` themselves and observe. This is a customer edit, not a
  skill action.
- Review the application's own access logs to see who is hitting the service and how often.

Windows (equivalent intent; exact commands were not confirmed in the source tickets, so treat the
specific commands as medium confidence and confirm before quoting verbatim):
- Use Task Manager / Resource Monitor for current per-process CPU, and review IIS / application
  logs for request sources.

## Attribution three-way (state the evidence, do not overclaim)

1. Platform infrastructure fault -> use the [incident and SLA guide](incident-sla-guide.md).
2. Customer application or a self-installed program -> the application owner analyzes app-side
   logs; the cloud-side monitoring only shows which process used resources, not its business
   meaning.
3. External access (attack, scraping, egress abuse) -> apply the stop-loss and hardening above.

## Standard wordings that keep the boundary honest

- Another account's identity: Alibaba Cloud cannot disclose another user's identity information.
  If the customer has reported to the police, judicial authorities may obtain it through legal
  process; at most a public geographic approximation may be shared.
- "Give me an official letter that the host is healthy": there is no such formal letter. The
  accepted substitute is a Cloud Monitor screenshot plus the ticket reply screenshot, sent by the
  customer to the counterparty.
- Historical process / traffic replay: not retained; real-time tools only.

## Hand-off

Compensation decisions, remote "on-behalf" configuration changes, and cross-account identity are
all outside this skill. Record the request, provide the evidence checklist, and route to the human
security / billing channel. See [hand-off boundaries](handoff-boundaries.md).
