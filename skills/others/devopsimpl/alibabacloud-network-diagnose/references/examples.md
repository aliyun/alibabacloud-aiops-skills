# Diagnosis Examples

## Same-VPC ECS Access Failure

Input:

```text
ECS i-bp111 cannot access ECS i-bp222 on TCP 3306 in cn-hangzhou.
```

Expected workflow:

1. Parse both instance IDs, region, protocol, and port.
2. Query both ECS instances and ENIs.
3. Query security group rules for both sides.
4. Check source egress and destination ingress.
5. Check forward and return VPC routes.
6. Check source and destination VSwitch NACLs.
7. Report every blocker, not only the first one.

## Cross-VPC CEN Failure

Input:

```text
VPC vpc-a in cn-beijing cannot access VPC vpc-b in cn-shenzhen through CEN cen-xxx.
```

Expected workflow:

1. Query CEN child instances.
2. Identify TR and VPC attachments.
3. Check association and propagation in both directions.
4. Check TR routes and VPC routes in both directions.
5. Check route maps if routes are missing or rejected.
6. Check TR zone VSwitch NACLs on both sides.

## VPN Gateway Failure

Input:

```text
VPC vpc-a cannot access IDC CIDR 172.16.10.0/24 through VPN Gateway.
```

Expected workflow:

1. Check VPC route to VPN Gateway.
2. Query VPN Gateway and IPsec connection state.
3. Use `TunnelStatusSummary` to determine active tunnels.
4. If VPC route and tunnel are normal, ask the user to verify VPN Gateway
   internal routes, including destination routes, policy routes, and BGP routes.

## NAT Gateway DNAT Asymmetric Return Path

Input:

```text
DNAT through NAT Gateway reaches backend ECS, but TCP does not establish. The
backend VPC is attached to CEN.
```

Expected workflow:

1. Query NAT Gateway, DNAT, and SNAT rules.
2. Check backend ECS return route toward the client IP.
3. Use longest-prefix match to detect whether a CEN propagated route overrides
   the NAT return path.
4. Report asymmetric routing when SYN enters through NAT but SYN-ACK exits
   through CEN.
