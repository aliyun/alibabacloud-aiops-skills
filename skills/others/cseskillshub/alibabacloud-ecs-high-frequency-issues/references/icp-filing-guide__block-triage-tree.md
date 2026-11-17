# Filing-Block Triage Tree (C2)

Who should read this: the agent, when a customer says a filed (or
filing-in-progress) website will not open, or suspects "the filing system is
blocking my site". The script `scripts/areas/icp_filing_guide/icp_filing_check.py triage` walks the
cloud-side half of this tree automatically; this file maps each script verdict
to the customer-facing explanation and the manual guidance that follows.

Ticket evidence shows the frequent truth: most "filed site cannot open" cases
are NOT filing interception. Observed root-cause ranking in the representative
tickets: security group missing 80/443 ingress (3 tickets - T-63E5332F,
T-7DFF74E6, T-AF9A4EAA) > DNS record missing (2 - T-16AB330B, T-3BE66325) > no
listener in the guest (1 - T-D9F63B3E) > genuine filing interception (1 -
T-FC32DAA3, and that attribution is summary-only, never transcript-verified).

## Quotable customer error strings

When the customer quotes `err_connection_closed` or `err_connection_reset`,
the connection is being torn down mid-stream. Ticket T-63E5332F
(transcript-verified) shows this exact shape - TCP connects, the HTTP/TLS
request dies after seconds, nothing in the server logs - and the root cause
was the security group NOT allowing 80/443 ingress, explicitly "unrelated to
filing synchronization". Routing rule:

- These strings send you to step 2 (security-group ingress) FIRST.
- Never present "the filing is blocking you" as the explanation for these
  strings unless steps 1-6 are all clear AND the customer's filing-console
  evidence shows a blocking state.

## The tree

How this maps onto the report `scripts/areas/icp_filing_guide/icp_filing_check.py triage` prints: its
numbered lines are Step 1 (locate the instance), Step 2 and "Step 2 conclusion"
(ingress rules), Step 3 (elastic IP state), then a Step 4 block titled "what the
cloud side cannot answer" that covers the three manual legs below - this file's
steps 4 (filing state), 5 (DNS) and 6 (guest listener). Do not look for printed
step numbers beyond 4.

```
Customer: "my filed website will not open / I think the filing blocks it"
|
|- 1. Locate the server (ecs DescribeInstances)
|     - instance found? status Running? fixed public IP or EIP present?
|     - Stopped instance / no public address -> that alone breaks public
|       access; report it, remediation is a customer console action.
|     - nothing found -> align on the instance ID / public IP / region with
|       the customer before anything else (ticket T-16AB330B shows customer
|       assumptions about which server hosts the site are often wrong).
|
|- 2. Security-group ingress for TCP 80 and 443
|     (ecs DescribeSecurityGroups + DescribeSecurityGroupAttribute,
|      rules of all bound groups merged, ascending priority, Drop wins at
|      equal priority, no match = default deny)
|     Per-group per-port verdicts (report `security_groups[].ports[]`):
|     - no_rule / no_allowing_rule / explicitly_dropped
|         -> merged verdict no_inbound_allow_rule or blocked_by_drop_rule.
|            Conclusion: security-group interception, UNRELATED to the
|            filing (T-63E5332F / T-7DFF74E6 / T-AF9A4EAA pattern).
|         -> give the manual console remediation below; this skill never
|            changes any rule.
|     - open_to_public -> merged verdict allowed; continue.
|     - limited_source_only -> merged verdict
|       allowed_for_narrow_source_only: the rule source CIDR is narrower than
|       the internet, so the public cannot reach the port. Treat as blocked
|       for public access and say which source range is allowed.
|     - a group whose rules failed to read produces a [WARN] line and an
|       entry in the report `errors[]`; that is a permission gap, and an
|       unread group is never read as "open" (if no group could be inspected
|       at all, the mode verdict is INSUFFICIENT_EVIDENCE).
|
|- 3. Public egress address state (vpc DescribeEipAddresses)
|     - EIP bound to the instance? Status InUse? Bandwidth > 0?
|     - anomalies here break reachability regardless of security groups.
|
|- 4. Filing status - NO API EXISTS IN THIS SKILL
|     - ask the customer for an ICP Filing console screenshot / the filing
|       number and state.
|     - filing still in progress or not passed: explain that domains
|       resolving to mainland servers without a completed filing may have
|       website access intercepted by the compliance mechanism, and that
|       testing via the server's public IP directly is the supported
|       workaround during the filing period (T-FC32DAA3 - summary-only
|       evidence; present as general guidance, not as a verified per-case
|       conclusion).
|     - filing passed -> continue.
|
|- 5. DNS resolution - NO API EXISTS IN THIS SKILL
|     - customer self-check in the Alibaba Cloud DNS console: does the apex
|       record "@" of the domain point at this server's public IP?
|     - tickets T-16AB330B (transcript-verified) and T-3BE66325
|       (summary-only): the site "was down" because only a subdomain record
|       existed while the apex domain had none.
|
|- 6. Guest listener - OUT OF THE READ-ONLY BOUNDARY
|     - this skill never runs commands inside the instance. Give the
|       customer the self-check guidance below; if the customer wants
|       hands-on guest diagnosis, hand off to
|       alibabacloud-ecs-diagnose or a server specialist.
|
|- All six clear and the site still fails ->
      route to the filing specialist (filing-side data this skill cannot
      read) and/or alibabacloud-ecs-diagnose for deep guest/network
      diagnosis, per references/icp-filing-guide__escalation-map.md.
```

## Manual remediation guidance (human steps only - never executed by this skill)

Security group (when step 2 finds 80/443 not open to the public):

1. Open the ECS console -> Network & Security -> Security Groups -> the group
   named in the script report. The report also prints the console path as a
   template (`.../region/{region}/groupId/{groupId}/detail/intranetIngress`);
   substitute the region and group ID from the report yourself.
2. In the Inbound direction, add an accept rule: protocol TCP, port range
   80/80 (and 443/443 for HTTPS), source 0.0.0.0/0.
3. Save; the rule takes effect immediately. Retest the website.
4. Official document: manage-security-group-rules (see
   `references/icp-filing-guide__help-links.md`).

Reminder for the agent: adding this rule is a WRITE action. This read-only
skill only prints the steps; the customer performs them. Never generate a CLI
command that would change the rule, and never offer to run it.

DNS apex record (when step 5 finds the "@" record missing):

1. Open the Alibaba Cloud DNS console -> the domain -> Add Record.
2. Record type A, host record @, value = the server's public IP printed by
   the script, TTL default. Save and retest after propagation.

Guest listener self-check (customer runs these on their own server):

- Linux: `ss -lntp` or `netstat -lntp` - is a web service listening on
  0.0.0.0:80 / 0.0.0.0:443 (not only 127.0.0.1)?
- Windows: `netstat -ano | findstr ":80"` / `":443"`.
- A freshly installed OS has NO web server running: nothing listening means
  the port refuses or times out even with perfect security-group and filing
  state (ticket T-D9F63B3E, summary-only). Deploying or starting the web
  service is server-side work -> `alibabacloud-ecs-diagnose`.

## Verdict-to-wording map (relay the script wording, do not invent)

Triage mode prints its conclusion in the report field `verdict`; eligibility
mode prints its account-wide conclusion in `verdict` too, with a per-instance
`verdict` inside each row.

| Script verdict | Say to the customer |
|---|---|
| `BLOCKED_BY_SECURITY_GROUP` | The security group does not allow public TCP 80/443; this interception is unrelated to your filing status. Follow the console steps above. |
| `NO_PUBLIC_ADDRESS` | The instance has no fixed public address and no EIP, so nothing on the internet can reach it yet; ask where the domain actually resolves today. |
| `NETWORK_PATH_CLEAR_FILING_STATE_UNKNOWN` | The cloud-side path is open; the remaining candidates are the filing state, the DNS apex record and the guest listener - walk steps 4-6 with the customer. |
| `INSTANCE_NOT_LOCATED` | The given instance/IP was not found in this account/region; re-align the identifiers with the customer before concluding anything. |
| `INSUFFICIENT_EVIDENCE` | No security group could be inspected for this instance; ask which group it uses (or grant `ecs:DescribeSecurityGroupAttribute`) and re-run. Never claim the path is open. |
| `ELIGIBLE_INSTANCE_FOUND` | The account does hold a server that can carry the filing service code; name the instance and bind the code to it in the same account. |
| `NO_ELIGIBLE_INSTANCE` | No instance in the scanned regions meets all three conditions; the report lists the exact missing condition per instance. |
| `NONE_FOUND` | No ECS instance was visible in the scanned regions - ask the customer which region the server lives in; if regions failed to answer, that is a permission gap, not an empty account. |
| per-instance `needs_confirmation` | A condition could not be read from the API (typically the subscription term): never report the instance as eligible - ask the customer to confirm it in the console. |

Where the report shows an EIP whose `status` is not `InUse`, or a rule set whose
allowed source is narrower than `0.0.0.0/0`, quote those printed fields directly
rather than inventing a verdict name for them.

## Evidence index for this tree

- T-63E5332F (transcript-verified): 80/443 ingress missing; "unrelated to
  filing synchronization"; connection torn down mid-request shape.
- T-16AB330B (transcript-verified): apex "@" record missing while a subdomain
  worked; first-line misattribution corrected by the second line.
- T-B57F5477 (transcript-verified, partially out of scope): DNS + security
  group inside this skill; Windows IIS/.NET deployment handed off.
- T-7DFF74E6, T-AF9A4EAA, T-3BE66325, T-D9F63B3E, T-FC32DAA3 (summary-only):
  same patterns; the filing-interception attribution of T-FC32DAA3 is NOT
  transcript-verified and must stay a hypothesis of last resort.
