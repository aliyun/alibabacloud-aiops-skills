---
name: alibabacloud-ecs-high-frequency-issues
area: icp-filing-guide
description: |
  Read-only ICP filing guide for Alibaba Cloud ECS: finds a filing-eligible server in the account, tells a security-group block apart from real filing interception, and explains filing service code and subject-change rules with manual console steps. Use when the customer's own wording mentions ICP filing. Triggers: my filed website will not open, filed domain shows blocked, no selectable instance for the filing service code, which ECS can be used for ICP filing, ICP filing subject change, new access filing for a filed domain, err_connection_closed, err_connection_reset. Do NOT use with no filing mention (alibabacloud-ecs-diagnose) or for VPC routing (alibabacloud-ecs-vpc-publicnetwork-troubleshoot); not for purchases, refunds, renewals, DNS edits or filing review status.
---

# ECS ICP Filing Guide (Read-Only)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Handles the "filing" area of ECS support work: whether a server may carry an
ICP filing service code, whether a filed site that will not open is really
blocked by filing, and what the filing rules cost the customer. Everything it
does is a read-only cloud query plus evidence-backed guidance; every remedy is
a step the customer performs in the console.

## 1. ABSOLUTE PROHIBITION - read-only boundary

This skill is **read-only**. You MUST NOT generate, write, or execute any
mutating cloud API call, in any form, including:

- a mutating call you would run yourself;
- a mutating call you hand to the customer as a command line to paste;
- a mutating call framed as "just to fix the security group quickly".

Concretely: the only actions this skill may issue are the five listed in the
whitelist below. Any request that would alter a resource, a security-group
rule, an order, an instance, a filing record or a guest operating system is
answered with console navigation steps and, where needed, a handoff. State the
boundary in one sentence, then give the manual steps.

Additional hard rules:

1. **Never run a command inside an ECS instance**, and never ask for or accept
   a remote-access password or authorization. Guest-side checks are printed as
   self-check guidance the customer runs themselves.
2. **Never call a filing, DNS, order or billing API.** No such contract was
   verified for this tier; filing state comes from the customer's console
   screenshot, never from a guess.
3. **Never answer from model memory.** Facts come from the scripts' API data or
   from the embedded evidence in `scripts/areas/icp_filing_guide/_constants.py` and `references/`.
   If neither has it, say so and route to a specialist.
4. **Never promise** a filing approval, a review expedite, a refund amount, the
   existence of a promotion, or an account unblocking.
5. **Do not attribute an outage to filing** until the security-group and
   public-address legs are clear. In the representative tickets, missing
   inbound rules and missing DNS records outnumbered genuine filing
   interception.

## 2. API whitelist

| Product | Action | Version | Purpose |
|---|---|---|---|
| ecs | `DescribeInstances` | 2014-05-26 | eligibility scan; locate the instance, its public address and its groups |
| ecs | `DescribeSecurityGroups` | 2014-05-26 | name the groups attached to the instance |
| ecs | `DescribeSecurityGroupAttribute` | 2014-05-26 | read inbound rules for TCP 80/443 |
| vpc | `DescribeEipAddresses` | 2016-04-28 | elastic IP binding and status |
| sts | `GetCallerIdentity` | 2015-04-01 | verify the credential and label the report with the account UID |

Anything outside this table is not permitted, and `scripts/areas/icp_filing_guide/_cli.py` refuses it
at runtime before a process is spawned. Full parameter and field detail:
`references/icp-filing-guide__api-contracts.md`. Minimum permissions:
`references/ram-policies.md`.

## 3. Prerequisites and credentials

- Requires the Alibaba Cloud CLI on `PATH`, configured through its normal
  profile mechanism. `scripts/areas/icp_filing_guide/_cli.py` reports a clean failure with the install
  and configure guidance when the CLI is absent.
- Credentials are resolved **exclusively by the default credential chain**.
  The scripts never read, accept, print, cache or forward a key or token, and
  no credential is ever passed on a command line. If the identity check fails,
  guide the user to the standard profile configuration command; never ask them
  to paste secret material to you.
- Run the optional pre-flight when account scoping matters:

  ```
  python3 scripts/areas/icp_filing_guide/sts_token.py
  ```

  It prints the account UID used as the traceability label in every report.

## 4. How to use it

Always go through the single entry point; never assemble cloud API calls by
hand.

```
python3 scripts/areas/icp_filing_guide/icp_filing_check.py selftest                  # offline logic check
python3 scripts/areas/icp_filing_guide/icp_filing_check.py eligibility               # C1: can any server carry the code?
python3 scripts/areas/icp_filing_guide/icp_filing_check.py triage --region cn-hangzhou --instance-id i-... [--domain example.com] [--symptom err_connection_reset]
python3 scripts/areas/icp_filing_guide/icp_filing_check.py knowledge --list-topics   # C3/C4: rule and routing bank
python3 scripts/areas/icp_filing_guide/icp_filing_check.py knowledge --query "<the customer's own words>"
```

Mode selection:

| The customer says | Mode |
|---|---|
| "I bought a filing service code and there is no instance to select" / "which server can I file with" | `eligibility` |
| "My site is filed but will not open" / "the filing system is blocking me" / `err_connection_closed` / `err_connection_reset` | `triage` |
| anything about timelines, subject change, cancelling and re-filing, access filing, expiry and renewal, MLPS paperwork | `knowledge --query` |
| "won't open" with **no** filing mention | out of scope - `alibabacloud-ecs-diagnose` |

Flags:

| Flag | Applies to | Meaning |
|---|---|---|
| `--region` | `triage` | region id such as `cn-hangzhou` (required there) |
| `--regions` | `eligibility` | comma-separated region list; default is the built-in mainland list |
| `--purchased-months` | `eligibility` | the instance's cumulative purchased length in months (original purchase plus renewals), read by the customer in the billing center; without it the script approximates from `CreationTime` to `ExpiredTime` and never fails a server for a short remaining term |
| `--instance-id` / `--public-ip` | `triage` | how to locate the server (one of the two) |
| `--domain` | `triage` | the domain the customer says is filed; drives the DNS guidance line |
| `--symptom` | `triage` | browser error wording, e.g. `err_connection_reset` |
| `--question` | `triage` | the customer's own words; scanned for the declared symptom strings |
| `--query` | `knowledge` | customer wording used to rank topics and routes |
| `--topic` | `knowledge` | print one topic key verbatim (see `--list-topics`) |
| `--limit` | `knowledge` | how many ranked topics to print (1-13, default 3) |
| `--profile` | all | named CLI credential profile |
| `--timeout` | all | per-call timeout in seconds (5-600, default 60) |
| `--json` | all | machine-readable output |

## 5. Evidence discipline and known blind spots

Every statement this skill makes about filing rules is tagged in the script
output and in `references/icp-filing-guide__filing-rules-faq.md` with its evidence level:

- `transcript-verified` - a real support conversation was read and matches;
- `summary-only` - only the ticket summary survived; when relaying it, keep the
  caveat "confirm this with a filing specialist";
- `partial-transcript` - the conversation was retrieved but truncated, same
  caveat.

Never upgrade a weaker tag to a stronger claim, and never relay a rule the
knowledge mode did not print.

The public cloud APIs used here cannot see, by design:

- live filing order state, filing number, filing subject, service-code
  inventory;
- DNS record contents (whether the domain apex has a record at all);
- what is listening inside the guest operating system;
- the cumulative purchased length of an instance (original purchase plus
  renewals). The official term condition is subscription billing whose
  purchased length is longer than 3 months, counted cumulatively across
  renewals and unrelated to usage time or remaining term (verbatim wording is
  kept in `references/icp-filing-guide__icp-eligibility-checklist.md`), so the
  remaining term is never a failure criterion here: the script uses
  `--purchased-months` when the customer reads the figure in the billing center,
  otherwise labels its `CreationTime`-to-`ExpiredTime` approximation and reports
  `unknown` rather than failing the server.

When the answer depends on one of those, ask the customer for the console
screenshot or route per `references/icp-filing-guide__escalation-map.md`. An unread fact is
reported as unread, never inferred.

## 6. Observability

Every API call this skill makes carries a per-run User-Agent so a whole session
can be correlated in the request logs:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session-id> skill-version/<skill-version>
```

That line is **internal**: the shared call layer appends it to every outgoing
CLI invocation. It is not a flag of `scripts/areas/icp_filing_guide/icp_filing_check.py`, and it must
never be typed by the user or added to the commands in section 4.

The `<session-id>` is a random 32-character hexadecimal value generated once per
script run (`uuid.uuid4().hex` in `scripts/areas/icp_filing_guide/_cli.py`) and attached to **every**
call of that run. It is a correlation label only: it contains no account,
resource or credential information, and is not stable across runs. The report
echoes the label so a finding can be traced back to one execution.

## 7. Degradation and failure handling

Each call has its own timeout, retries transient throttling and 5xx failures
with backoff, masks any credential-shaped text in error output, and degrades
without stopping: a failed leg prints `[WARN]`, lands in the report's `errors`
list, and the remaining legs still run.

- Authorization failures surface the API error code verbatim (`NoPermission`,
  `ImplicitDeny`) together with the single missing action from the whitelist
  table, so the policy can be widened minimally.
- A query that returns nothing is a **finding**, not an error. Say what was
  scanned and what came back.
- If the data needed for a verdict is missing, the script says so and the
  correct next step is to ask the customer, not to fill the gap in.

## 8. Output contract

End every answer by relaying the script's closing contract honestly:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next instruction the script printed>
```

- `OK` - the queries succeeded and the verdict is evidence-backed.
- `DEGRADED` - a usable conclusion, but at least one leg was unreadable; name
  the leg.
- `FAIL` - no conclusion is available; ask for the missing input instead of
  reasoning around it.

Also declare any parameter the skill filled in by itself (the mainland region
scan list, the account UID label, the page-size limits) and quote only numbers
and identifiers that appear in the output. This skill never applies a fix; it
reports, explains, and routes.

## 9. References

- `references/icp-filing-guide__icp-eligibility-checklist.md` - the three filing-server conditions, how each is judged, service-code rules.
- `references/icp-filing-guide__block-triage-tree.md` - the filed-site-will-not-open decision tree and verdict wording.
- `references/icp-filing-guide__filing-rules-faq.md` - rule and consequence wordings with evidence tags.
- `references/icp-filing-guide__escalation-map.md` - boundary recognition and handoff routes.
- `references/icp-filing-guide__help-links.md` - official documents and entry points, with verification status.
- `references/icp-filing-guide__api-contracts.md` - parameters and fields of the five read actions.
- `references/ram-policies.md` - least-privilege read-only policy.
