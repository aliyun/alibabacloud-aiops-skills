# Auto Scaling + Load Balancer Integration (Scenario: scaled-out instances receive no traffic)

Scope: "we configured Auto Scaling but the new servers are not used while
the old one stays busy", "how do new instances start receiving traffic",
"how should the database / cache be shared after scale-out".

All configuration actions below are CUSTOMER console actions. This skill
outputs the step guidance, cross-checks the cloud-visible facts read-only
(instance state, zone spread, whether the instance is still producing
load), and never changes anything.

> Source discipline: calibers are distilled from real support tickets of
> this tier plus the verified ECS high-availability architecture document:
> https://help.aliyun.com/zh/ecs/user-guide/hablog.md
> Official SLB/ESS product documentation URLs are PENDING verification;
> never invent a URL.

## Mechanism (why new instances "are not used")

1. Auto Scaling only creates instances. Traffic reaches an instance only
   when the instance is attached to the load balancer's server group
   (rule `SCALING-MUST-ATTACH-LB`).
2. In a properly configured scaling group, the LB server-group attachment
   is declared in the scaling configuration, so every scale-out instance is
   attached automatically; health checks then gate whether it RECEIVES
   requests -- an unhealthy new instance gets no traffic even when
   attached.
3. If customers created extra instances manually (outside the scaling
   group), nothing attaches them: they must be added to the server group
   in the console (customer action) or brought under the scaling group.

## Standard architecture steps (customer-executed; guidance only)

1. Prepare a custom image from a configured golden instance so scale-out
   instances start with the application installed.
2. Create the load balancer (CLB/ALB/NLB per
   `references/slb-backend-diagnosis__lb-selection-matrix.md`) with a listener and a server group.
3. Create the scaling group; in the scaling configuration, select the custom
   image and declare the LB server-group attachment; set min/max/desired
   capacity and the scaling rules (e.g. CPU-based).
4. Point the application on new instances at SHARED data endpoints: the
   database / cache must be addressed by a routable endpoint (managed
   service, or the source server's private IP), never 127.0.0.1
   (rule `SCALING-SHARED-STATE`). Session state must not live only on one
   instance (externalize sessions or enable session persistence on the
   listener -- console option, customer action).
5. Enable the scaling group and run a scale-out test; verify in the SLB
   console server group that the new instance appears and its health-check
   status turns healthy (console fact the customer returns).
6. Bandwidth for scaled instances: public bandwidth is configured per the
   scaling configuration / instance network setup (customer console
   action); this skill only reads EIP facts (`vpc DescribeEipAddresses`).

## What this skill verifies read-only

- Given the backend instance IDs: status, zone spread, instance type,
  security-group bindings (`ecs DescribeInstances`); whether each instance
  is still producing CPU/traffic (`cms DescribeMetricLast`, latest
  datapoints only, as a CLUE); EIP status/bandwidth when the entry point
  uses an EIP.
- NOT verifiable here (customer console facts): server-group membership,
  health status per backend, listener session-persistence settings, scaling
  group rules.

## Verification loop

After the customer completes the steps: the customer returns (a) the server
group listing with health status and (b) a load test result. The entry
script re-checks the cloud-visible facts; the conclusion "new instances now
receive traffic" is only stated when the returned evidence shows it.

## Cited documents (verified links only)

- High-availability architecture (LB + multi-zone + Auto Scaling):
  https://help.aliyun.com/zh/ecs/user-guide/hablog.md
- ECS overview: https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md
