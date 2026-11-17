# Logon-credential decision tree (branches LC1-LC9)

This is the knowledge backing `scripts/areas/login_credential_repair/login_credential_diagnose.py`. The same
branch codes are printed verbatim in the report, so a finding can always be
traced back to a node in this file. The machine-readable copy of the phrase
dictionary and the taxonomy lives in `scripts/areas/login_credential_repair/_constants.py`
(`ERROR_DICTIONARY`, `ROOT_CAUSE_TAXONOMY`); this document is the human
narrative and must stay aligned with it.

## 1. What this tree decides

One question, in this order:

1. Is the failure on the credential area at all, or on a neighbouring area
   (transport, instance state, resources, security, application layer)?
2. If it is the credential area: which of the nine branches explains it?
3. What is the smallest set of manual steps that confirms or kills that branch?

The tree never decides "execute this". Every leaf is a guided human action
behind the gates in `../SKILL.md` ("Permission model and safety gates").

## 2. Step 0 - the boundary test (always first)

| Observation | Area | Action |
| --- | --- | --- |
| The port answers and a logon prompt or logon screen appears, but the credential is refused | credential (this skill) | continue into the tree |
| The port never answers, the session times out before any prompt, or the client cannot reach the service | transport / security group | hand off, see [handoff-scripts.md](login-credential-repair__handoff-scripts.md) |
| The instance will not boot, or is stuck between states | instance state | hand off |
| Logon succeeds but the session is black, lagging, or the service was not running | resources / services | hand off after noting the credential worked |

Boundary vs `alibabacloud-ecs-linux-os-troubleshooting`: that skill owns
general Linux operating-system faults (boot, kernel, network configuration,
services). This skill stops at "is the credential and the account usable".

Why the test comes first: in the evidence for this tier the single most
expensive mistakes were made by engineers who trusted a "wrong username or
password" style message and escalated to a snapshot plus in-guest
investigation, when the customer had in fact dialed the private IP address.
Ruling the transport area out costs one question and no authorization.

## 3. Branch taxonomy

| Code | Branch | What it means | Typical confirmation |
| --- | --- | --- | --- |
| LC1 | Client-side path or cached credential | Wrong endpoint (private IP instead of public), non-default remote port, client or Workbench replaying remembered credentials, RDP username prefixed with the local computer name | Instance facts show the address actually reachable; the same credential works from a console session |
| LC2 | Wrong logon username for this image | The image forbids direct root logon or expects `ecs-user` / `cloud-user`; the assumed user does not exist in the guest | The server names the expected user in its own refusal; guest user list confirms |
| LC3 | Online reset channel not usable | The console online reset needs the cloud assistant agent; the agent is offline, or the invocation failed, or the task reports success while the password never changed | `DescribeCloudAssistantStatus` plus `DescribeInvocations` records |
| LC4 | Key pair interference | The instance is bound to a key pair, key-only logon is enforced, or the referenced key pair no longer exists | `DescribeInstances` binding plus `DescribeKeyPairs` existence in the same region |
| LC5 | Account locked | The lockout policy is in effect for the attempted account, usually after repeated failed logons, frequently from internet traffic against an openly exposed remote-desktop port | Read-form policy query; the console lock message |
| LC6 | Account disabled or nonexistent | The account is disabled, deleted, or never existed (built-in administrator, guest, or an assumed Linux user) | Account-state query; guest user list |
| LC7 | Reset write blocked by the guest environment | The guest cannot apply the write: disk full, security software interference (never verified), or an offline reset still waiting for one restart | Instance state; guest free-space reading; explicit customer statement of the console error |
| LC8 | Credential knowledge gap | The password cannot be viewed and can only be reset; the customer does not know the default username or the console entry | Direct answer, no measurement needed |
| LC9 | Out-of-scope area detected | Transport, instance state, resources, suspected intrusion, application-layer credential, commercial questions | Route to [handoff-scripts.md](login-credential-repair__handoff-scripts.md) |

Branches co-exist. A Windows instance can be LC5 (locked) and LC3 (the online
reset that was attempted never reached the guest) at the same time, and LC1
can survive after the server side is fixed. The report therefore prints every
branch that evidence supports, not a single winner.

## 4. Phrase-to-branch dictionary

Matching is case-insensitive substring matching on the verbatim text the
customer or the console produced. The embedded dictionary in
`scripts/areas/login_credential_repair/_constants.py` also carries the verbatim Chinese console wording that
customers paste, which is why this page only lists the English forms.

| Phrase (customer or console wording) | Branch | Meaning shown in the report |
| --- | --- | --- |
| `Please login as the user '...' rather than the user 'root'` | LC2 | The image forbids the attempted user and names the expected one |
| `Connection closed by <address> port 22` | LC2 | The transport answered and the server then refused: a policy or credential refusal, not a network fault |
| `for security reasons ... account has been locked` | LC5 | Lockout policy in effect |
| `the referenced account is locked and may not be logged on` | LC5 | Same lockout, different Windows edition wording |
| `too many logon attempts or password changes` | LC5 | Same lockout, reason text |
| `your credentials did not work`, `authentication error` | LC1 | Client-side refusal; not by itself proof the password is wrong |
| `account is disabled`, `has been disabled` | LC6 | Disabled account |
| `user ... does not exist` | LC6 | The assumed account is not in the guest |
| `key pair has been removed`, `Permission denied (publickey)` | LC4 | Key-pair logon involved: binding, removal, or key-only enforcement |
| `instruction execution failure`, `execution failed`, `reset failed` | LC3 | The online reset or its delivery channel did not complete |
| "the task shows success but the new password still fails" | LC3 | Hidden failure: the write never reached or never applied |
| `no space left on device`, disk-space wording during a reset | LC7 | A guest limit blocks the password write; expansion is out of scope |
| `forgot`, `lost my password`, `where can I see the password` | LC8 | Knowledge gap |
| private IP, a non-default port number, remembered or cached credentials, computer-name prefix | LC1 | The client is talking to the wrong endpoint or replaying stale credentials |
| security-group whitelist, deny rule, ransomware, encrypted files, virus, instance will not start, panel password, website 500, "run as administrator" for an installer, memory or CPU exhaustion | LC9 | Neighbouring area |

Deliberate non-matches (false-hit control, all from evidence in this tier):

- A bare `administrator` is not a trigger. It only counts next to a logon,
  lock or password context, otherwise installer and UAC permission errors
  ("the program needs permission to install") land in this skill.
- "Cannot connect" is not a trigger by itself; step 2 decides.
- "Password" only counts for the ECS instance logon credential, never for an
  application panel or website backend.
- "Under attack" stops the workflow and routes to the security incident
  process; this skill identifies and does not remediate.

## 5. Evidence each branch needs, and where it comes from

| Fact needed | Source | Automatable |
| --- | --- | --- |
| OS family, instance state, public and private addresses, key-pair binding | `DescribeInstances` / `DescribeInstanceAttribute` | yes |
| Whether the online reset channel can work at all | `DescribeCloudAssistantStatus` | yes |
| Whether a referenced key pair still exists in the region | `DescribeKeyPairs` | yes |
| Whether a reset or command ever reached the guest | `DescribeInvocations` | yes |
| Which logon users actually exist inside the guest | guest reading, customer-executed | no (see [guest-credential-checks.md](login-credential-repair__guest-credential-checks.md)) |
| Effective lockout threshold and account state | guest query form of the account commands | no |
| Failed logon counts and their source address | guest security log | not covered today |
| Security-group source ranges and deny rules | console | no API is called by this skill |
| Whether the remote port is the default one | guest listening-socket reading | no |

Turning the first four rows into facts is the point of this skill: in the
ticket evidence for this tier, "the agent was probably broken" and "security
software must have intercepted the reset" were asserted repeatedly and never
measured. The first is now measurable; the second is not, and stays a
hypothesis.

## 6. Confidence labels

Every finding is printed with one of three labels; the agent must relay them
unchanged.

| Label | Meaning | Rule |
| --- | --- | --- |
| `CONFIRMED` | An API field or the verbatim console text proves it | Quote the field |
| `REPORTED` | The customer says so, nothing measured | Attribute to the customer |
| `HYPOTHESIS` | A plausible mechanism that was not measured | State the missing measurement and how to get it |

Security-software interception of a password reset, "the server is under
brute-force attack", and a hypervisor-side cause for a failed console
operation are `HYPOTHESIS` by construction. They must never be printed as
causes.

## 7. Convergence and stop rules

- One pass: boundary test, then the four automated reads, then branch
  assignment. If the reads are all healthy and the credential still fails,
  the tie-breaker is a console interactive session with the same credential
  (it separates a client-path problem from a real credential problem).
- Fixed round limit: if after the boundary test, the reads, and the tie-breaker
  the branch is still unresolved, stop with `STATUS: DEGRADED` and hand the
  remaining step to a human engineer. Do not escalate into guessed writes.
- Anything destructive or state-changing is never the "next small step": the
  ladder stops at guidance plus a risk statement.

## 8. Open points carried from the requirement review

These are deliberately unresolved; the skill's defaults are the conservative
column, and none of them may be silently "improved":

| # | Open point | Default shipped here |
| --- | --- | --- |
| 1 | Whether the in-guest command whitelist is extended to cover the credential area | Not extended: the scripts dispatch no in-guest command; the readings in [guest-credential-checks.md](login-credential-repair__guest-credential-checks.md) are customer-executed |
| 2 | Whether the skill may reset a password on the customer's behalf | No: console path plus online/offline difference and restart impact |
| 3 | Which unlock instruction is authoritative (clear the lockout threshold, enable the account, or an interactive sign-in) | All three listed side by side in [windows-lockout-playbook.md](login-credential-repair__windows-lockout-playbook.md), each labeled un-reconciled; the threshold write is flagged as a policy write |
| 4 | Preferred in-guest carrier (Workbench versus Cloud Assistant) | Neither is dispatched; the console guidance documents both entry paths |
| 5 | Windows query command shape | Query forms only, confidence marked medium |
| 6 | Exact snapshot call shape (per-disk versus all disks of an instance, name, consistency group) | Console guidance only; API shape left TODO, system-disk coverage stated as a requirement |
| 7 | Whether failed-attempt forensics is in scope | No: reported as a known capability gap |
| 8 | OpenAPI error codes for the reset and command actions | No code table exists in the evidence: routing uses customer wording plus API fields, and no code is invented |
| 9 | Cloud Assistant polling interval, ceiling, output length limit | No magic numbers: a call that does not succeed degrades immediately |
| 10 | Security-group read and write APIs | Not declared, not called; guidance only |
| 11 | Programmatic VNC entry | Not declared; console navigation text only |
| 12 | Disk capacity and monitoring reads | Not declared; identified-and-handed-off instead |
| 20 | Titles of the numeric-id help pages cited by support | Listed with a TODO in [help-docs.md](login-credential-repair__help-docs.md) |
| 21 | Whether a snapshot rollback also rolls back the logon password | Operational note at low confidence, never a causal claim |
| 22 | Whether console key-pair binding is still unavailable for Windows images | Stated as a low-confidence operational note to verify in the console |
