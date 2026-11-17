# Degraded output when the customer's resources are not visible - full wording

Unabridged form of the MANDATORY rule summarised in SKILL.md under "Degraded output
when the customer's resources are not visible". Every clause binds; the summary is not a
licence to skip any of it. The root-cause examples below are drawn from resolved tickets
and are maintainer evidence: rank them for the stated symptom, and never present one as a
confirmed cause without a read that covers it (SKILL.md report-spine rules 1-3).


Empty results under the current credentials do NOT mean the problem does not exist: tickets are
resolved by the support engineer's checklist, not by the account view. When any queried
instance/disk/domain/bill returns empty, NotFound, or Forbidden, you MUST NOT stop at
"query failed" or ask the customer to restate the issue. You MUST still output, for the stated
symptom:
1. the layered check order the customer can run in their own account, with the exact aliyun CLI
   commands (use the command shapes from the area reference);
2. the ranked high-frequency root causes for this symptom drawn from real tickets - for example
   root-partition inode exhaustion from many small files; enterprise security group default
   deny-egress blocking DNS (UDP 53); DDoS blackhole state making a site unreachable; stopping
   state stuck by in-guest processes or Windows update; service-linked role deletion blocked by
   dependent services; Workbench/CLI tool not installed in the guest; image vs kernel version
   mapping for marketplace OS images; domain resolution using @ record or wrong link-local
   address; expired or no-stock conditions for spec changes; GPU driver and CUDA mismatch;
   CC-attack or high connection counts saturating nginx; arrears-triggered bandwidth limits;
3. which finding confirms which root cause, and the escalation condition when all checks pass.
Never change customer resources: never fabricate readings, never claim a specific cause without evidence - rank
probabilities and say what evidence would confirm each. The ban is symmetric over NEGATIVE exclusions (MANDATORY):
"it is NOT a quota problem", "not an inventory issue", "unrelated to billing" are claims too - a factor may be
eliminated ONLY by a read that covers it; factors living in internal backends invisible to the leg (risk-control
verdict, quota approval records, off-ticket conversations) MUST NEVER be excluded nor confirmed, and instead be
split into separate conditional determinations that each name the customer-visible channel it belongs to
("if the block reason is a quota ceiling -> the offline business/SA channel; if it is a violation flag -> the
appeal path"). Ruling out an invisible factor is the most common unverified assertion in real tickets and is a
defect even when the remaining direction is correct. Equally mandatory: probe results describe ONLY the
resources visible under the current credentials - if the customer's own domain/instance is NOT among them,
you MUST NOT assert that resource is healthy, deployed, or reachable; mark it UNVERIFIED and put it in the
layered checklist instead.
