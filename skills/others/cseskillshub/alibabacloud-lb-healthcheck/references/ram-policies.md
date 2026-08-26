# RAM Policies

This skill is strictly read-only. The following RAM policy grants only the
read actions actually invoked by the diagnosis scripts (via the aliyun CLI).
No wildcard actions and no write actions are required or declared.

## Read-Only Policy (recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "slb:DescribeLoadBalancerAttribute",
        "slb:DescribeLoadBalancerTcpListenerAttribute",
        "slb:DescribeLoadBalancerUdpListenerAttribute",
        "slb:DescribeLoadBalancerHttpListenerAttribute",
        "slb:DescribeLoadBalancerHttpsListenerAttribute",
        "slb:DescribeRules",
        "slb:DescribeRuleAttribute",
        "slb:DescribeVServerGroupAttribute",
        "slb:DescribeMasterSlaveServerGroupAttribute",
        "slb:DescribeHealthStatus",
        "alb:GetLoadBalancerAttribute",
        "alb:ListListeners",
        "alb:ListRules",
        "alb:GetListenerHealthStatus",
        "alb:ListServerGroups",
        "alb:ListServerGroupServers",
        "nlb:GetLoadBalancerAttribute",
        "nlb:ListListeners",
        "nlb:GetListenerHealthStatus",
        "nlb:ListServerGroups",
        "nlb:ListServerGroupServers",
        "vpc:DescribeVSwitches",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Action-to-Script Mapping

| Product | Action | Used By | Purpose |
|---------|--------|---------|---------|
| SLB | DescribeLoadBalancerAttribute | diagnose_clb.py | Instance attributes, listener list, default backends, VpcId |
| SLB | DescribeLoadBalancerTcpListenerAttribute | diagnose_clb.py | TCP listener health-check config |
| SLB | DescribeLoadBalancerUdpListenerAttribute | diagnose_clb.py | UDP listener health-check config |
| SLB | DescribeLoadBalancerHttpListenerAttribute | diagnose_clb.py | HTTP listener health-check config |
| SLB | DescribeLoadBalancerHttpsListenerAttribute | diagnose_clb.py | HTTPS listener health-check config |
| SLB | DescribeRules | diagnose_clb.py | Forwarding rules per listener |
| SLB | DescribeRuleAttribute | diagnose_clb.py | Rule detail and rule health-check config |
| SLB | DescribeVServerGroupAttribute | diagnose_clb.py | vServer group backends |
| SLB | DescribeMasterSlaveServerGroupAttribute | diagnose_clb.py | Master/slave group backends |
| SLB | DescribeHealthStatus | diagnose_clb.py | Backend probe status per listener |
| ALB | GetLoadBalancerAttribute | diagnose_alb.py | VpcId, ZoneMappings, probe source IPs |
| ALB | ListListeners | diagnose_alb.py | Listener enumeration (paginated) |
| ALB | ListRules | diagnose_alb.py | Forwarding rules per listener |
| ALB | GetListenerHealthStatus | diagnose_alb.py | Probe status including rule-bound groups |
| ALB | ListServerGroups | diagnose_alb.py | Server group attributes |
| ALB | ListServerGroupServers | diagnose_alb.py | Server group backend servers |
| NLB | GetLoadBalancerAttribute | diagnose_nlb.py | VpcId, ZoneMappings, probe source IPs |
| NLB | ListListeners | diagnose_nlb.py | Listener enumeration (paginated) |
| NLB | GetListenerHealthStatus | diagnose_nlb.py | Probe status per listener |
| NLB | ListServerGroups | diagnose_nlb.py | Server group attributes |
| NLB | ListServerGroupServers | diagnose_nlb.py | Server group backend servers |
| VPC | DescribeVSwitches | diagnose_alb.py, diagnose_nlb.py | Resolve zone vSwitch CIDRs |
| STS | GetCallerIdentity | _cli.py | Verify caller identity (best effort) |
