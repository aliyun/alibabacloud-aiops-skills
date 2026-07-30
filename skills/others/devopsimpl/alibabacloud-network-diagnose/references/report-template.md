# Diagnosis Report Template

Use this structure for the final answer.

## Conclusion

One sentence that states whether private connectivity is expected to work and
the most likely root cause.

## Check Summary

Render a Markdown table with these columns:

| Check | Result | Evidence |
|-------|--------|----------|
| Instance state | ok/warning/critical/skipped | Key resource state |
| Security group | ok/warning/critical/skipped | Matched rule or no match |
| Route table | ok/warning/critical/skipped | Forward and return next hop |
| Network ACL | ok/warning/critical/skipped | Matched rule or no ACL |
| Cross-network connection | ok/warning/critical/skipped | Peering/CEN/VPN/VBR state |
| NAT Gateway | ok/warning/critical/skipped | DNAT/SNAT and return path |

## Root Causes

List all root causes in P0 to P3 order. Do not stop after the first issue.

## Recommended Actions

Provide exact remediation steps. For CEN-origin routes, do not suggest direct
route deletion. Suggest a more specific static route or CEN route-map change
when appropriate.

## Detailed Evidence

Show route tables in this chain:

`Instance -> VSwitch -> Route Table -> Matched Route -> Next Hop`

Include both forward and return paths.
