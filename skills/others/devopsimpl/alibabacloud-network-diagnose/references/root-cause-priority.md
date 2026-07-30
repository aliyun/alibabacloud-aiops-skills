# Root Cause Priority

Use this order when ranking findings in the final diagnosis report.

## P0 Critical

- Destination ECS is stopped, deleted, or not in VPC network.
- Security group or network ACL explicitly denies the requested protocol/port.
- Forward or return route has no match.
- Matched route is blackhole or points to an unavailable next hop.

## P1 High

- Cross-VPC connection is missing or unhealthy.
- CEN Transit Router association or propagation is missing.
- VPN tunnel has no active IPsec SA.
- DNAT return path bypasses the NAT Gateway because a more specific CEN route
  wins longest-prefix match.

## P2 Medium

- Protocol or port is unspecified, so rule matching cannot be exact.
- Some product permissions are missing and the related checks were skipped.
- Route map policy may reject learned routes.
- VPN Gateway internal routes are ambiguous or mix destination, policy, and BGP
  routes.

## P3 Informational

- No network ACL is bound to a VSwitch.
- OS firewall checks are outside this skill and should be verified by the user
  only when all cloud-side checks are normal.
