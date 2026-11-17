# Ticket Pattern Library (distilled from the injected sample dialogues)

Ground truth for how human support resolved each cluster — the skill mirrors
these paths with instant, reproducible decoding instead of screenshot
round-trips. Anonymization: usernames, account ids, resource-group ids and
request ids are replaced with placeholders; wording is translated to English.
Conversation source: tickets marked *(full dialogue)* were reviewed verbatim
in the injection; tickets marked *(summary only)* had no retrievable dialogue
and are used as summary-level evidence — no steps were invented for them.

## Cluster A — grant exists yet denial persists (scope x context)

**T-EE03C367** *(full dialogue)* — RAM user with `AliyunECSFullAccess`
attached still got a RAM denial inside the mobile ECS console.
- Staff flow after several screenshot rounds: the identity actually held
  only a **resource-group-scoped** grant (`rg-…` group), not the account-level
  one; web context fixed after account-level guidance; on the phone the fix
  was **"tap 'All Resources' at the top-left, then pick the resource group"**.
- Customer asked the canonical trade-off question — "can't we grant only per
  resource group? I don't want all ECS shared with everyone" — staff: yes,
  for a few specific servers; the main account performs it in the RAM
  console. Staff additionally advised checking custom policies for **Deny**
  rules, and pasted doc ids 2669110 / 39743 (see `help-docs.md`).
- Customer confirmed resolved.
- Skill equivalent: denial decode → `grant-context-mismatch` branch →
  `ecs:DescribeInstances` visibility + actual resource group → scope model
  table + mobile-app step + Deny audit.

**T-8FE09114** *(summary only)* — `RunInstances` 403 ("not authorized on the
specified resource, or the API does not support RAM"). Root causes per
summary: wildcard Action must pair with wildcard Resource; creating instances
reuses an existing VSwitch yet still needs explicit VPC/VSwitch grants.
Customer complained the error never says **which** permission is missing —
the skill's answer must always land on a concrete action/scope, never
"please check your permissions".

**T-2B09C359** *(full dialogue)* — Alibaba Cloud Client showed a RAM denial.
Staff attributed it immediately ("the RAM sub-account lacks ECS instance
operation permissions") and pasted the console path: main account → RAM
console Users → find sub-account → Add Permissions → search
`AliyunECSFullAccess`. After the grant the denial path was resolved (weak
confirmation — customer pivoted to a VNC-graphical question, which is the
connection-method area, handled by handoff).

## Cluster B — fine-grained action gaps in feature chains

**T-296B2D19** *(full dialogue)* — installing web VSCode from Workbench:
`User has no permission to do the action: (ListExecutionRiskyTasks)`.
- Key exchanges: staff — "the Workbench install needs **OOS** permissions";
  customer pasted the needed policy (multi-product: bss / ecs / oos / oss
  actions, reproduced as template t4 in `policy-templates.md`) asking "why do
  I need a billing permission?"; staff clarified "**OOS**, not OSS — the
  install rides on the OOS operations-management feature".
- Skill equivalent: bracket-token extraction → product resolution (OOS ≠ OSS
  caveat is built into the catalog) → full-chain template in one answer.
- Closure note: customer never confirmed success after the paste — the
  template is the ticket-evidenced remedy, labelled ticket-cited.

**T-39B65627** *(summary only)* — repeated "no permission" inside ECS
Workbench; staff identified missing `ecs-workbench:ChatMessages`, suggested
system policy `AliyunECSWorkbenchFullAccess` or a custom policy with that
action; customer could not find the permission item in the picker, staff
provided the policy text. Constraint: this action does not support
per-instance narrowing (Resource must keep the wildcard form).

**T-2D30AEF6** *(full dialogue)* — "can I create a sub-account AccessKey with
view access to all cloud hosts, their costs and expiry?" The online session
collected the requirement and escalated to an offline engineer — **unresolved
in-channel**. This is the planning-consult gap the skill standardizes: t6
(verified names) + an explicit "billing data is outside verified names, here
is the handoff" statement.

## Cluster C — sub-account / AccessKey / least-privilege planning

**T-169ADF41** *(full dialogue)* — first-time ECS buyer asked how the
"super admin account" works, where passwords are set, how to create a
permission-limited sub-account for a third party. Staff answer: default OS
admins, password setting, RAM console user creation with specified
permissions; pasted `https://ram.console.aliyun.com/users`; a follow-up phone
call closed it. Skill equivalent: t6 + scope model + OS-user-vs-RAM-user
note, instantly and consistently.

**T-71463C20** *(partial — phone ticket, 2 dialogue lines)* — "create two
admin **login** accounts on our Ubuntu ECS for engineers" — an
**OS-user/RAM-user layer confusion**; staff guided instance credentials,
then least-privilege hardening post-deployment. The retrievable dialogue does
not cover the staff's verbal explanation — treated as summary evidence.

**T-87674B21** *(full dialogue)* — customer proactively asked "our RAM
account has full permissions — could this be account-related?" while a disk
detach silently failed. Staff proved it was NOT authorization (the
platform-side engineering review found a guest-side occupancy; advised
relinking the agent via restart, and resmon
to find the holding process). This is the reference exemplar for
**recognize-and-handoff**: an operation rolling back with an empty error is
not a denial (see exclusion table in `error-signals.md`).

## Cluster D — roles, service-linked roles, role grants

**T-0217BF77** *(full dialogue)* — following the "auto-reboot on high CPU"
(Cloud Monitor + OOS) tutorial, stuck at role creation/authorization. Staff
dictated the exact parameters (Trusted entity = Cloud Service; Trusted
service = the operation-orchestration service; then grant
`AliyunECSFullAccess` **to the role**, e.g. `OOSServiceRole`). Customer hit
"cannot find this policy" — a console-picker search trap (System Policies
tab) — completed, confirmed working. Skill equivalent: role-flow steps +
search-position tip + handoff to the tutorial doc after authorization.

**T-8FA544FE** *(summary only)* — service-linked role created by accident
while enabling a DevOps product; customer asked staff to delete it.
Hard boundaries evidenced here: service-linked roles are customer-self-service
only; staff may not operate customer accounts; the customer's missing real-name
verification blocked the RAM console entirely — ticket ended in account
cancellation (outside our scope; account-area handoff).

**T-E55C752C** *(summary only)* — frequent attacks, CPU pinned; customer
suspected a link to an earlier AccessKey leak and attacker-created malicious
sub-accounts. Staff in-guest review found the dominant issue was security
groups exposing ports 22/6379 to all IPs; source-IP restriction and backups
advised. Co-occurrence lesson for the AK-leak branch: always re-check
security groups (handoff), and key disabling stays manual (see the containment
section of `policy-templates.md`).

## Cluster E — bucket noise: recognize + hand off (9 of 20 injected samples)

| Ticket | Customer wording | Actual area | Handoff line (skill output) |
|---|---|---|---|
| T-913B2393 | "ordering button fails: blocked by cors policy" | customer web code | CORS is configured in your application; contact your site developers — server resources are not involved. |
| T-D0578489 | "the client can't see my servers, wrong account?" | China vs International site | The two sites keep separate accounts; switch the client to the site your account belongs to. |
| T-337347EB | "cannot release, the status does not support this operation" | resource lifecycle/billing | This is a state limitation, not a permission denial; handle dependencies then release in the console — released resources cannot be recovered. |
| T-920B4F23 | "snapshots keep charging and won't delete" | image dependency + billing | A snapshot referenced by a custom image cannot be deleted first; see snapshot billing. |
| T-28ED5673 | "BIOS image won't boot on the new generation" | instance-state/image | Boot-mode problem on the image side; handed to the instance-state area. (Also the ticket showing staff entering the guest **after asking the customer for authorization** — the confirmation-gate practice patterned by this skill.) |
| T-7621C755 | "main account has no permission to change the security group" (Jushita) | platform managed policy | Inside Jushita, security groups are applied through the Jushita console; ECS-console edits are inert there. |
| T-D5229C33 | "allow only my IP's AccessKey login to port 22, disable password" | security-group capability limit | Security groups filter IP/port only — they cannot distinguish SSH authentication methods. |
| T-50DCE95E | "sub-account ECS expired and was released, restore my data" | backup/restore | Without a snapshot or image, released data is unrecoverable — a platform-mechanism limit, not a permission. |
| (pattern) | anything matching `AliyunServiceRoleFor*` deletion requests | RAM self-service | Self-service only, with the real-name prerequisite; never executed by staff or this skill. |

Misconception phrases the decoder recognizes verbatim (translated): "I
already gave it AliyunECSFullAccess" (scope mismatch), "and account-related?"
(T-87674B21-style over-attribution to RAM), "is it the OSS permission?"
(OOS/OSS letter swap), "the client can't see my servers" (site area),
"the status does not support this operation" (lifecycle area).

## Staff-behaviour invariants the skill keeps

1. Staff never execute grants for customers — always main-account manual
   console operations; the skill matches this exactly (no RAM calls).
2. In-guest inspection happens **after** telling the customer what will be
   done and getting a yes (tickets T-28ED5673 "authorize and I'll take a
   look", T-E55C752C); the skill's `--guest-check` gate encodes the same
   step with an observation-only whitelist.
3. Snapshot-before-risky-cleanup is the standing staff script (T-2B09C359
   pasted create-a-snapshot and snapshot-billing docs); the skill's snapshot
   doc pointers live in `help-docs.md` — the skill itself performs no
   snapshots or cleanup.
4. Answers that would be guessed (unverified action names, cost APIs) become
   declared gaps + handoffs — never invented permission points.
