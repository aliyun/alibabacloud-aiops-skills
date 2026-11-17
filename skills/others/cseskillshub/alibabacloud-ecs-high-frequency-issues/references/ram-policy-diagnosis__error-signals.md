# Error & Symptom Signals: Decode -> Branch -> Evidence

Primary input of the diagnosis is the **customer's error text exactly as
received** (`scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py --error-text`). This file is the
human-readable expansion of the embedded pattern tables in
`scripts/areas/ram_policy_diagnosis/_constants.py` (denial signals, exclusion signals, capability
chains, branch titles). Vocabulary note: per the batch auth-failure literal
rule, this documentation reports denials under the `NoPermission` /
`ImplicitDeny` family; customer-pasted strings stay opaque input to the
decoder and are never reproduced from memory.

The tier spec provided NO quotable error-code table for this tier; every
signal below is distilled from the injected ticket dialogues/summaries
(ticket IDs are the evidence anchors).

## 1. Denial signals (case may belong to this skill)

| Signal id | What matches | Meaning | Typical next branch |
|---|---|---|---|
| `http-403` | `403` appears | authorization-denied status | sub-branch by other clues |
| `no-permission` | "no permission" wording / NoPermission family code | explicit denial | action-gap or scope check |
| `not-authorized` | "not authorized" wording | explicit denial | action-gap or scope check |
| `deny-rule-hit` | ImplicitDeny / deny-rule wording | a Deny statement or missing Allow in evaluation | Deny audit (checklist step 4) |
| `ram-tagged-denial` | denial attributed to RAM in the text | the denial names the RAM layer | scope/syntax checks first |
| `ram-suffixed-code` | an error **code** whose trailing segment names the RAM layer (matched by code shape, not by a fixed string) | the platform stamped the rejection as a RAM authorization outcome | scope/syntax checks first -- this is what still classifies when the customer pastes only the code, with no HTTP status and no prose |
| `access-refused` | "cannot see / cannot operate / you do not have permission" | refusal or invisibility without a code | console-context questions |

## 2. Action-gap extraction

Two customer-visible shapes carry the missing permission **inside** the
message:

- `User has no permission to do the action: (<Name>)` -- the parenthesised
  token is extracted as the action name and resolved against the product
  catalog (pattern in `ACTION_EXTRACT_PATTERNS`). Evidence: ticket
  T-296B2D19 (`ListExecutionRiskyTasks` -> OOS, not OSS).
- "you are not authorized to operate the specified resource, or this API
  does not support RAM" alongside a named API such as `RunInstances`.
  Evidence: ticket T-8FE09114. This shape points at an **invalid
  Action/Resource combination** (see syntax rule 1) plus a cross-product
  dependency (VPC/VSwitch reads), NOT at a missing single action.

Resolution output always carries an evidence label: a name in this skill's
verified call surface (`sts:GetCallerIdentity`, `ecs:DescribeInstances`,
`ecs:run-command`, `ecs:DescribeInvocations`) vs a **ticket-cited** name
(known customer-facing names seen in real dialogues: `ecs-workbench:ChatMessages`,
`oos:StartExecution`, `oos:ListExecutionRiskyTasks`,
`ecs:DescribeInvocationResults`, `ecs:DescribeCloudAssistantStatus`,
`bss:DescribeOrderDetail`, `oss:GetObject`). Ticket-cited names are never
invoked by this skill -- they appear only in labelled templates
(`references/ram-policy-diagnosis__policy-templates.md`).

## 3. Exclusion signals (recognize + handoff, do NOT treat as RAM)

Real-bucket noise is high (9 of 20 injected samples are not RAM at all), so
the first decision-tree step is genuine-permission detection:

| Signal id | Customer wording | Why not RAM | Handoff area (evidence ticket) |
|---|---|---|---|
| `operation-state-blocked` | "the status does not support this operation" on release/change | resource lifecycle state gate | billing / resource lifecycle (T-337347EB) |
| `browser-cors` | "blocked by cors policy" | browser-side application config | customer's developers (T-913B2393) |
| `security-group-semantics` | ports, source IPs, "allow only my IP to ssh" | reachability is security-group semantics; SG cannot distinguish SSH key vs password login | security-group area (T-D5229C33) |
| `empty-error-state-rollback` | "detach failed, no error message, status rolled back" | platform could not read guest state; process occupancy | guest-side disk/agent area (T-87674B21) |
| `site-account-system` | "the client cannot see my servers, wrong account?" | China-site vs International-site account systems are separate | account area (T-D0578489) |
| `platform-managed-policy` | "main account has no permission in Jushita" | platform-side managed policy rules | Jushita platform docs (T-7621C755) |
| `snapshot-dependency-billing` | "snapshot cannot be deleted / keeps charging" | custom-image dependency, billing | billing / image area (T-920B4F23) |
| `boot-image-failure` | BIOS image fails to boot on UEFI generation (dracut timeout) | image boot mode | instance-state / image area (T-28ED5673) |
| `expired-release-data` | "sub-account instance expired, restore my data" | no permission path; without snapshot/image unrecoverable | backup/restore area (T-50DCE95E) |
| `realname-blocked` | "cannot enter RAM console" | account real-name verification gate | account area (T-8FA544FE) |
| `connection-method-limit` | "client does not support VNC / graphical" | client capability | remote-connection area (T-2B09C359) |

Handoff lines must cite the matching URL from `references/ram-policy-diagnosis__help-docs.md` and
the ticket id above -- the same links staff used in those tickets.

## 4. Confusion traps this skill corrects (from ticket dialogues)

- **OSS vs OOS** (T-296B2D19): web-VSCode install rides on OOS (Operation
  Orchestration Service), one letter from OSS. Prefix resolution is explicit
  in the catalog.
- **OS user vs RAM user** (T-71463C20): creating login accounts *inside*
  Ubuntu is an instance-credential topic; RAM answers console/API identity.
- **"granted = everywhere visible"** (T-EE03C367): a resource-group-scoped
  grant is invisible outside that group's console context -- including the
  mobile app's top-left "All Resources" picker.
- **"every blocked action is a permission problem"** (T-87674B21,
  T-337347EB, T-7621C755): run the exclusion table first.
- **API name != RAM action name** (batch rule, CMS/bss examples): never
  derive a RAM action from an apiName; only verified or ticket-cited names
  are output, each labelled.
- **Policy search "cannot find the policy"** (T-0217BF77): switch the grant
  picker to the System Policies tab before searching for a system policy.

## 5. Four-step root-cause checklist (K2 order)

1. **Syntax validity** -- wildcard Action entries must pair with wildcard
   Resource entries; actions without resource-level scoping never match
   instance-scoped grants (T-8FE09114, T-39B65627).
2. **Scope x console context** -- account vs resource-group vs tag grants;
   verify the instance's actual resource-group binding with
   `ecs:DescribeInstances` (verified); switch console context accordingly.
3. **Cross-product action gap** -- resolve the denied action's owning
   product; grant the whole feature chain (Workbench/OOS/Cloud Assistant
   templates in `references/ram-policy-diagnosis__policy-templates.md`).
4. **Identity placement & Deny audit** -- user vs role grant location
   (`sts:GetCallerIdentity` says what the presenting credential is); any
   attached `Effect: "Deny"` statement overrides every Allow (T-EE03C367
   staff advice).

## 6. Status contract

The entry script ends every run with `STATUS: OK|DEGRADED|FAIL` plus a single
`NEXT_ACTION:` line. `DEGRADED` always accompanies `[WARN]` evidence lines
(which call failed, impact, and the missing-action hint when the *diagnostic
credential itself* is denied) -- relay them verbatim; never re-run denied
calls through other channels or invent their results.
