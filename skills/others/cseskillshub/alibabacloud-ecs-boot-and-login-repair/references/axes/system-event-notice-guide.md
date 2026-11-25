---
name: alibabacloud-ecs-system-event-notice-guide
description: |
  Read-only guide for ECS instance system events and scheduled maintenance notices. Reads instance facts and running status with Describe* actions only, interprets the notice wording, and returns an evidence-based report with the steps the customer performs.
  Use when a customer received a maintenance or reboot notice and asks why it was sent, what the event state means, the deadline, or whether data or the IP is affected.
  Triggers: "ECS system event", "scheduled maintenance notice", "reboot required due to system maintenance", "my ECS restarted on its own", "operation and maintenance notice", "region shutdown notice", "Instance:StoragePerformanceReachLimit", "event status shows canceled".
  Do NOT use to read guest OS logs or log into the instance, to reboot, reschedule or snapshot anything, to size disk performance or alert rules, or for migration execution and refund approvals.
---

# ECS system events and scheduled maintenance notices

Answer the customer's question about an ECS system event or maintenance notice -
why it was sent, what its state means, what the deadline is, what happens to the
data and the IP - from read-only cloud facts plus documented rules, and hand the
customer the console steps they perform themselves.

## Read-only boundary

This section is an **ABSOLUTE PROHIBITION**, not a preference. It applies to the
scripts, to any command the agent proposes, and to any snippet shown to a
customer to paste:

- The only cloud calls this skill makes are the reads named in the
  `ALLOWED_READ_ACTIONS` allowlist in
  [scripts/axes/system_event_notice_guide/_constants.py](scripts/axes/system_event_notice_guide/_constants.py), repeated in
  [related_apis.yaml](related_apis.yaml) and
  [references/ram-policies.md](references/ram-policies.md). The shared call
  layer refuses anything outside that allowlist.
- Never call, generate, or recommend an action that changes a cloud resource:
  nothing that modifies, creates, deletes, releases, resets, replaces, attaches,
  detaches, reboots, starts, or stops anything, and no renewal, refund, or
  ticket-submission call of any kind. A read-only skill must never declare or
  imply a write permission.
- Never run a command **inside** an instance: no SSH, no Session Manager, no
  Cloud Assistant command execution, no VNC. Guest-side work is handed to the
  customer as a checklist in
  [references/system-event-notice-guide__customer-selfcheck-steps.md](references/system-event-notice-guide__customer-selfcheck-steps.md).
- Requests such as "reboot it for me", "move the restart time", "take the
  snapshot", "claim the compensation", "check whether the host is healthy" are
  **refused politely**: state the boundary, give the console path or the ticket
  route, and stop. Do not half-execute them.

If a customer needs a change performed, they do it in the console or through a
human handler; this skill supplies the rule and the path.

## Prerequisites

- Alibaba Cloud CLI installed and already configured for the target account.
  Credentials come from the default credential chain that the CLI resolves on
  its own. This skill never asks for, reads, echoes, or stores a credential
  value; if no identity resolves, tell the customer to run `aliyun configure`
  outside this skill.
- The read permissions in [references/ram-policies.md](references/ram-policies.md)
  attached to that identity. A denial is reported with the labels
  `NoPermission` or `ImplicitDeny` plus the missing action, never as a guess.
- Visibility limits: only instances inside the credential's account and
  authorised regions are readable. An instance the customer names but that
  returns nothing is reported as unreadable, never as "no event".

## How to run it

One entry point only. Do not compose cloud calls by hand and do not bypass the
script: the script is the single place where the read-only allowlist, the
timeouts, and the user agent are enforced.

```bash
python3 scripts/axes/system_event_notice_guide/ecs_system_event_notice.py \
  --region-id cn-hangzhou \
  --instance-id i-example0000000001,i-example0000000002 \
  --notice-text "reboot required due to system maintenance" \
  --output md
```

Variants you will actually need:

```bash
# Notice wording only, no instance named yet (explain the rules, then ask for the id)
python3 scripts/axes/system_event_notice_guide/ecs_system_event_notice.py --region-id cn-hangzhou \
  --notice-text "the maintenance event was automatically canceled"

# Resolve by the IP that appears in the notice
python3 scripts/axes/system_event_notice_guide/ecs_system_event_notice.py --region-id cn-hangzhou --private-ip 172.16.0.38

# Batch inventory of the ids a customer pastes
python3 scripts/axes/system_event_notice_guide/ecs_system_event_notice.py --region-id cn-hangzhou \
  --instance-id i-example0000000001 --instance-id i-example0000000002 --output json
```

| Parameter | Required | Notes |
|---|---|---|
| `--region-id` | yes | The region of the instance; every read is scoped to it. |
| `--instance-id` | one selector | Repeatable or comma separated. |
| `--private-ip`, `--public-ip` | one selector | Resolved to instance records through the read action. |
| `--notice-text` | recommended | The notice wording rendered into English; see step 2. |
| `--timeout` | no | Per-call timeout, defaults to the constant in `scripts/axes/system_event_notice_guide/_constants.py`. |
| `--profile` | no | CLI profile name, never a credential value. |
| `--output` | no | `md` (default) or `json`. |

Exit codes: `0` for `STATUS: OK`, `1` for `STATUS: DEGRADED`, `2` for `STATUS: FAIL`.

## Workflow

1. **Collect the minimum.** Region plus an instance ID or the IP from the notice,
   plus the notice wording. If the wording is not in English, translate the key
   phrase into the English wording used by the tables in `scripts/axes/system_event_notice_guide/_constants.py`
   before passing `--notice-text`, and keep the customer's original text in the
   conversation so the mapping can be re-checked.
2. **Run the entry script** and read its report; do not restate anything it did
   not return.
3. **Interpret through the rules**, never from memory:
   [references/system-event-notice-guide__event-status-semantics.md](references/system-event-notice-guide__event-status-semantics.md)
   for what each state means and what it implies for the deadline, and
   [references/system-event-notice-guide__notification-playbook.md](references/system-event-notice-guide__notification-playbook.md)
   for the seven recurring misreadings and their correct answers.
4. **Answer the four questions the customer always has**: why this happened, do I
   still have to act, what is the latest time, and what happens to my data and my
   IP. Each answer carries its source and its confidence.
5. **Give the customer the steps** they perform themselves from
   [references/system-event-notice-guide__customer-selfcheck-steps.md](references/system-event-notice-guide__customer-selfcheck-steps.md):
   where to see the event, reboot now, schedule the reboot, snapshot, auto-start
   on boot, and which guest logs they can read on their own.
6. **Hand off what this skill cannot do**, per
   [references/system-event-notice-guide__boundary-handoff.md](references/system-event-notice-guide__boundary-handoff.md), and say so in
   one line rather than hedging.
7. **Close with the report contract** below.

## Report contract

| Field | Meaning |
|---|---|
| `STATUS: OK` | The reads the skill declares ran, and the report contains instance facts, a notice interpretation, or both. |
| `STATUS: DEGRADED` | Part of the evidence is missing: a read failed, the identity did not resolve, no selector matched, or nothing matched the notice wording. Say what is missing and where to get it. |
| `STATUS: FAIL` | Nothing could be established. Report the failure text and the smallest next step. |
| `NEXT_ACTION:` | The single next move, always a manual or customer-side one. |

Rules when presenting it: quote only values the script returned; keep the
`warnings` and `Read failures` sections in the answer; never upgrade "no record
read" into "no event exists"; keep the limitations block verbatim because it is
the part customers most often misread.

## Known limitations of this build

- **Event records are out of reach.** No action that reads the instance system
  event list or its state has been verified for this skill, so the report never
  contains event rows. Event existence and state are therefore answered from the
  console page the customer opens, or from a ticket - never from this skill. This
  is the single most important thing to state before any conclusion.
- **Host health and migration destination are not exposed to customers** through
  any supported read. If asked, say the platform does not publish it and offer
  the ticket route.
- **State names are provisional.** The labels in
  [references/system-event-notice-guide__event-status-semantics.md](references/system-event-notice-guide__event-status-semantics.md)
  cover the states seen in the reviewed support cases only; the full official
  state machine is not verified here.
- **Reference URLs are not re-fetched by this build.** Open the linked help page
  before quoting a rule as official, and treat any statement marked
  `not verified` as provisional.
- **Nothing after the deadline is visible here**: whether a reschedule request
  was granted, whether a migration finished, or whether a claim was approved.

## Handoff phrasing

Use the shape, filling in the specific gap: "This needs *guest log access / a
configuration change / a commercial approval*, which is outside this read-only
skill. You can *step plus document*, or submit a ticket for *category*."

## Observability

Every cloud call this skill makes carries a user agent built from one session id
generated per run:

```
--user-agent AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

`{skill}` is `alibabacloud-ecs-system-event-notice-guide` and `{session-id}` is
the per-run id. `new_session_id()` in [scripts/axes/system_event_notice_guide/_cli.py](scripts/axes/system_event_notice_guide/_cli.py) produces
that id as a 32-character lowercase hex string with `uuid.uuid4().hex`, and
`build_user_agent()` attaches it to every invocation, so one customer question
maps to one traceable call group. The id is echoed in the report header for
correlation; no credential value is ever part of it.

## Files

| Path | Purpose |
|---|---|
| [scripts/axes/system_event_notice_guide/ecs_system_event_notice.py](scripts/axes/system_event_notice_guide/ecs_system_event_notice.py) | Single entry point: selectors, reads, interpretation, report. |
| [scripts/axes/system_event_notice_guide/_cli.py](scripts/axes/system_event_notice_guide/_cli.py) | Shared call layer: user agent, per-call timeout, bounded retry, masking, error labels. |
| [scripts/axes/system_event_notice_guide/_constants.py](scripts/axes/system_event_notice_guide/_constants.py) | Allowlist, limits, doc references, notice families, state and handoff tables as code constants. |
| [scripts/axes/system_event_notice_guide/sts_token.py](scripts/axes/system_event_notice_guide/sts_token.py) | Identity reachability check and masked account tag. |
| [references/ram-policies.md](references/ram-policies.md) | Minimum read-only policy, action by action. |
| [references/system-event-notice-guide__event-status-semantics.md](references/system-event-notice-guide__event-status-semantics.md) | Event families, states, deadlines, data and IP rules. |
| [references/system-event-notice-guide__notification-playbook.md](references/system-event-notice-guide__notification-playbook.md) | Notice wording to answer, including the common misreadings. |
| [references/system-event-notice-guide__customer-selfcheck-steps.md](references/system-event-notice-guide__customer-selfcheck-steps.md) | Steps the customer performs in the console or inside the OS. |
| [references/system-event-notice-guide__boundary-handoff.md](references/system-event-notice-guide__boundary-handoff.md) | Where each adjacent symptom goes and what to say. |
