# Detailed Rules and Feature Workflows

> This file is the on-demand deep-read supplement of [SKILL.md](../SKILL.md). For routine queries the Agent only needs the SKILL.md index; when executing mutating operations or needing full rule details, jump to the corresponding section of this file via the links in SKILL.md.

## References Index <a id="references-index"></a>

> Full sub-document index (manual troubleshooting / new-member onboarding / offline lookup entry; at runtime the Agent deep-reads on demand via the SKILL.md links):

| Category | Document | Purpose |
|---|---|---|
| **Environment setup** | [cli-installation-guide.md](./cli-installation-guide.md) | Complete guide for Aliyun CLI installation, upgrade, credentials and eflo-controller plugin configuration (macOS/Linux/Windows) |
| **Quick reference** | [command-quick-reference.md](./command-quick-reference.md) | Core CLI command quick-reference table (list/describe/extend/shrink/...), for manual troubleshooting and newcomer onboarding |
| **API reference** | [api-parameters.md](./api-parameters.md) · [endpoint-routing.md](./endpoint-routing.md) · [supported-regions.md](./supported-regions.md) · [error-codes.md](./error-codes.md) · [ram-policies.md](./ram-policies.md) | API parameters, endpoint routing, regions, error codes, RAM policies |
| **Business workflows** | [extend-cluster.md](../workflows/extend-cluster/extend-cluster.md) · [shrink-cluster.md](../workflows/shrink-cluster/shrink-cluster.md) · [create-node-group.md](../workflows/create-node-group/create-node-group.md) · [update-node-group.md](../workflows/update-node-group/update-node-group.md) · [delete-hyper-node.md](../workflows/delete-hyper-node/delete-hyper-node.md) · [node-operations.md](../workflows/node-operations/node-operations.md) | Scaling, node group, hyper node, node operations |
| **Queries** | [cluster-query.md](../workflows/cluster-query/cluster-query.md) · [node-group-query.md](../workflows/node-group-query/node-group-query.md) · [hyper-node-query.md](../workflows/hyper-node-query/hyper-node-query.md) · [../workflows/machine-image-query/machine-image-query.md](../workflows/machine-image-query/machine-image-query.md) | Query paths for each resource |
| **Rule details** | [detailed-rules.md](./detailed-rules.md) (this file) · [edge-cases.md](./edge-cases.md) · [scripts.md](./scripts.md) | Full rules, edge scenarios, script contracts |
| **mutating schemas** | [workflows/<biz>/schema.yaml](../workflows/README.md) | confirmation-table templates and forbidden_inference field definitions per action |

---

## Parameter Confirmation — Full Rules <a id="parameter-confirmation"></a>

> 🛑 **BLOCKING GATE — Two-Phase Commit (MANDATORY)**: All mutating CLIs (`extend-cluster` / `shrink-cluster` / `delete-*` / `change-node-group` / `create-node-group` / `update-node-group` / `bssopenapi create-instance`) **must** be issued via the [`safe_mutate` two-phase flow](scripts.md#safe_mutate-two-phase-commit-mandatory): the Agent internally generates a parameter confirmation table (with hash-based integrity check) and presents it to the user; the user reviews and replies with the confirmation word (the localized "confirm" phrasing) to approve, after which the Agent internally executes the real CLI. Region / ClusterId / NodeGroupId / MachineType / ImageId / VpcId / VSwitchId / SecurityGroupId / Hostname / LoginPassword(`******`) / BillingType / Amount **must all** appear in the confirmation table; VPC / VSwitch / SecurityGroup are flagged `forbidden_inference` — the LLM is **strictly forbidden** from auto-filling values after a `MissingParameter` error or silently inheriting cluster parameters. Per-action schemas live in [`../workflows/`](../workflows/README.md) — full confirmation-table templates are in each schema's `summary_order` / `merged_form_template` sections.
>
> **User-facing confirmation flow**: The user sees only a clean parameter confirmation table and is asked to reply with the localized confirm word to proceed or the cancel word to abort. Internal mechanism terms (`safe_mutate` / `APPROVE_TOKEN` / `hash` / `Phase 1` / `Phase 2` / `dry-run`) are **strictly hidden** from the user per [§Agent Output Surface Control](#agent-output-surface-control) (internal-mechanism terminology hard rule).

### Intent → Action Binding — Extended Rules <a id="intent-action-extended"></a>

**Error-recovery hard rule**: when the target action cannot be executed due to a CLI error (`ChargeTypeViolation` / `OperationConflict` / `NotFound` / "subscription nodes cannot be released", etc.), the Agent's **only allowed path** is to return to HITL and explicitly disclose three things to the user — ① the action corresponding to the original intent, ② why it cannot be executed (original error code + business meaning), ③ provide 1–N candidate actions for the **user** to choose (e.g. "release failed → switch to shrink (nodes return to the free pool but keep billing)" / "release failed → switch to migration into a free group (nodes stay in the cluster but leave the business group)"). The Agent is **strictly forbidden** from deciding a substitute action on its own and then entering the two-phase commit.

**Post-hoc narrative whitewash ban (hard rule)**: after a mutating action completes, narratives such as "logical shrink / equivalent to / the actual effect is / an indirect implementation / achieves the logical purpose of XX / in business semantics this is XX" are **strictly forbidden** — they rationalize the process of transforming the originally intended action A into B. Any actual execution inconsistent with the user's original intent must first ⚠️ V7 self-report + discard the result, then return to HITL; see [edge-cases.md §4.5 V7 + generic anti-whitewash clause](edge-cases.md#45-skill-self-violation-not-retryable).

**Agent self-check hard rule (MANDATORY)** — this Skill **does not rely on any shell-level physical gate**. `lib/safe-mutate.sh` is currently a minimal implementation (parameter dump + decoupling of two function calls only); it does **not** auto-compare intent vs action inside the wrapper, does **not** auto `exit 11`, and does **not** auto-write the HITL state file. All responsibility for detecting intent drift rests on the Agent itself:

**Invocation form (recommended / retained)**: `safe_mutate <action> --intent "<user's original words>" aliyun eflo-controller ...` — `--intent` immediately follows the action, and its value is the user's most recent business-request sentence that triggered this operation (placeholder phrases like "execute operation" / "user has confirmed" are **strictly forbidden**). The current purpose of this `--intent` field is mainly to be **written into `audit.log` for post-hoc accountability**, and to serve as the Agent's formal trace that "I did perform the self-check".

**Before generating each mutating command, the Agent MUST internally output a self-check block** (invisible to the user, but present in the Agent's own thinking / draft area):

```
[intent self-check · internal]
user original words : <the most recent sentence carrying a business action verb>
matched keywords    : <kw1, kw2 ... ← taken from the user_intent_keywords single source of truth below>
action to map       : <action-from-table>
action about to run : <action-about-to-execute>
forbidden_inference fields:
  - VpcId/VSwitchId/SecurityGroupId/ImageId/Hostname/LoginPassword: did the user explicitly provide them in HITL? ✅ / ❌
consistency verdict : ✅ consistent → proceed to Phase 1 / ❌ inconsistent → ABORT + write HITL state file + HITL disclosure
```

**Failing to output the self-check block = V7 violation** (same tier as intent drift, **non-retryable, non-pardonable**). The keyword scan table (**single source of truth**) lives in the `user_intent_keywords:` section at the top of [`../workflows/<biz>/schema.yaml`](../workflows/README.md); before each mutating operation the Agent **MUST `read_file` the corresponding yaml** to fetch that list, and **must not** reuse it from memory. If no keyword entry matches (the user used novel words like "decommission / retire / phase out") → **MUST** offer a HITL two-way choice for the user to pick; the Agent **must not** adjudicate on its own.

**HITL state file write responsibility**: when the self-check fails / an async task reaches a non-terminal state / any V1-V7 self-violation ABORT occurs, the Agent **MUST proactively** execute `jq -n '{...}' > $HOME/.lingjun/hitl-required.json` (schema in [§HITL State File Check](#hitl-state-file-check)). The script layer does **not** write this file on the Agent's behalf.

**User-surface shielding**: terms such as `--intent` / `audit.log` / "self-check block" are internal constraints; per [§Agent Output Surface Control Rule 1](#agent-output-surface-control) they are **strictly forbidden** from appearing in user-facing text (including tool-call descriptions).

### Concurrent Mutating Operations (MANDATORY) <a id="concurrent-mutating-operations"></a>

Within the same cluster, `extend-cluster` and `shrink-cluster` (and other mutating actions among themselves) **may be submitted concurrently**; the Agent is **not** required to wait for prior `TaskId`s to reach a terminal state. Specific rules:
1. **HITL disclosure obligation**: In the concurrency step of the F2 / F3 workflow, if `describe-cluster` returns a non-empty `TaskId`, the Agent **must** show the user "Active task: `TaskId=<tid>` / operation=<extend|shrink|...>" and offer two choices: a) submit immediately in parallel (default) / b) wait for the prior task to terminate. The Agent is **strictly forbidden** from deciding "wait / don't wait" on its own.
2. **No automatic retry on server-side rejection**: After the user picks a), if the server returns `OperationConflict` / `The cluster is not in Running state, not allowed to extend.` (see [error-codes.md L121 / L152](error-codes.md)), this falls into the business 4xx blacklist — the Agent is **forbidden** from silently retrying or auto-polling, and must immediately bubble back to HITL so the user can re-decide (retry / cancel / wait for the prior terminal state then resubmit).
3. **Independent polling for both tasks**: After successful concurrent submission, extend / shrink each obtain an independent `TaskId` and **must** be polled separately via `describe-task` every 30s, without interference; a business failure on one task does not affect the state determination of the other.
4. **Irreversible confirmation retained**: the "confirm" step of F3 shrink is **fully retained** under concurrency semantics and cannot be omitted; the hard rule on the source of the resource-list field for irreversible operations applies equally.
5. **fallback compatibility**: When the user actively picks b) the "wait" path, the polling script in [edge-cases.md §4.4](edge-cases.md#44-concurrent-operation-conflict-operationconflict) (30s polling ≤ 30min) may be reused; that script is enabled **only on explicit user choice** and is **no longer** the Agent's default conflict response.

Violating any of the above is treated as a Skill self-violation on par with [edge-cases.md §4.5 V2/V3](edge-cases.md#45-skill-self-violation-not-retryable) (bypassing two-phase commit / auto-filling `forbidden_inference`): **non-retryable, non-pardonable**.

### `forbidden_inference` Parameter Hard Rule (MANDATORY) <a id="forbidden-inference"></a>

In mutating-call schemas, fields flagged `forbidden_inference` (typically: `VpcId` / `VSwitchId` / `SecurityGroupId` / `ImageId` / `Hostname` / `LoginPassword`) are **strictly forbidden** from being auto-filled by the LLM from conversational context / `describe-cluster` responses / historical commands / other resources in the same Region, or silently inherited from cluster parameters. After a `MissingParameter` error, the Agent **must** route through HITL: invoke `list-vpcs` / `list-vswitches` / `list-security-groups` / `list-images` and similar list-* APIs so the user **explicitly picks** from the real inventory (no default inference / context reuse / "looks reasonable" fills allowed). Any LLM auto-fill of a `forbidden_inference` field constitutes [edge-cases.md §4.5 V3](edge-cases.md#45-skill-self-violation-not-retryable) — **non-retryable, non-pardonable**: stop immediately, retract all auto-filled values, discard the pending parameter set, disclose to the user in the format `⚠️ Skill violation (V3): <specific facts>, <obtained results> have been discarded; restarting from the list-* HITL`, then restart from the list-* HITL. Per-action `forbidden_inference` field lists live in [`../workflows/`](../workflows/README.md).

> **Legitimate authorization path exception (added by 2026-05 governance, not V3)** — only when **both** of the following conditions are satisfied simultaneously may the Agent take the ground-truth `VpcId` / `VSwitchId` / `SecurityGroupId` from `describe-cluster` / `describe-node-group` and write them into the submission parameters: ① the user **explicitly selects** the "reuse cluster network config" / "reuse source node-group network config" option in HITL; ② the form displays the **real ID value field by field** (placeholders such as "(inherited)" / "<inherit>" are not allowed), annotated with "source: describe-cluster ClusterId=<cid>" / "source: describe-node-group NodeGroupId=<gid>". If either condition is missing, the Agent still handles it per this section's hard rule. It is **strictly forbidden** to skip passing the fields on the pretext of "reuse cluster network config" — that was the pre-2026-05-governance semantic fraud (the user believes the cluster VPC was passed, while the CLI actually passed nothing), handled at the same tier as V3: **non-retryable, non-pardonable**. The full flow is in the `inherit_cluster_network_policy:` section of [`../workflows/extend-cluster/schema.yaml`](../workflows/extend-cluster/schema.yaml).

---

## API Version Whitelist (MANDATORY) <a id="api-version-whitelist"></a>

> 🛑 **Hard rule** — this Skill's eflo-controller CLI **allows only Version=2022-12-15 (1215) APIs**. The Agent must not invoke any non-whitelisted action in any scenario.

### Background

After installing the eflo-controller CLI plugin, actions from multiple historical versions are exposed simultaneously (e.g. `list-nodes`, the 0706-version `describe-instance`, etc.). Fields returned by these legacy interfaces are incompatible with the 1215 version (different field names, different enum values, different field sets). Typical cases:

- **Forbidden** `list-nodes` → use `list-cluster-nodes`; the "work status" (`Shutdown`/`Running`/`Stopped`) fields returned by the former do not exist in the 1215 version;
- **Forbidden** `describe-instance` → use `describe-node`;
- **Forbidden** any `--version 2022-07-06` or `--version 2024-04-25` parameter.

### Full Whitelist

#### eflo-controller (Version=2022-12-15)

| # | CLI action | OpenAPI name | Type |
|---|---|---|---|
| 1 | `list-clusters` | ListClusters | read-only |
| 2 | `describe-cluster` | DescribeCluster | read-only |
| 3 | `list-cluster-nodes` | ListClusterNodes | read-only |
| 4 | `extend-cluster` | ExtendCluster | async mutating |
| 5 | `shrink-cluster` | ShrinkCluster | async mutating |
| 6 | `describe-node` | DescribeNode | read-only |
| 7 | `delete-node` | DeleteNode | mutating |
| 8 | `list-node-groups` | ListNodeGroups | read-only |
| 9 | `describe-node-group` | DescribeNodeGroup | read-only |
| 10 | `create-node-group` | CreateNodeGroup | mutating |
| 11 | `update-node-group` | UpdateNodeGroup | mutating |
| 12 | `change-node-group` | ChangeNodeGroup | async mutating |
| 13 | `list-free-nodes` | ListFreeNodes | read-only |
| 14 | `list-free-hyper-nodes` | ListFreeHyperNodes | read-only |
| 15 | `list-hyper-nodes` | ListHyperNodes | read-only |
| 16 | `list-cluster-hyper-nodes` | ListClusterHyperNodes | read-only |
| 17 | `describe-hyper-node` | DescribeHyperNode | read-only |
| 18 | `delete-hyper-node` | DeleteHyperNode | mutating |
| 19 | `list-machine-types` | ListMachineTypes | read-only |
| 20 | `list-images` | ListImages | read-only |
| 21 | `describe-task` | DescribeTask | read-only |
| 22 | `describe-regions` | DescribeRegions | read-only |
| 23 | `describe-zones` | DescribeZones | read-only |
| 24 | `delete-node-group` | DeleteNodeGroup | mutating |

#### Other Namespaces

| Namespace | CLI action / OpenAPI | Purpose |
|---|---|---|
| `bssopenapi` | `create-instance` | Lingjun order placement / purchase |
| `bssopenapi` | `get-subscription-price` | Query subscription pricing |
| `bssopenapi` | `get-pay-as-you-go-price` | Query pay-as-you-go pricing |
| `ecs` | `describe-images` | Query custom images |
| `vpc` | `describe-vpcs` | V3 repair path: list-vpcs lets the user explicitly pick VpcId |
| `vpc` | `describe-vswitches` | V3 repair path: list-vswitches lets the user explicitly pick VSwitchId |
| `ecs` | `describe-security-groups` | V3 repair path: list-security-groups lets the user explicitly pick SecurityGroupId |

### Ghost-Field Ban

The Agent is **strictly forbidden** from rendering or referencing to the user any field that does not belong to the 1215-version return values. Typical ghost fields:

| Ghost field | Source | Correct 1215 counterpart |
|---|---|---|
| "work status" (`Shutdown`/`Running`/`Stopped`) | 0706/0425 `list-nodes` | 1215 `list-cluster-nodes` returns `OperatingState` |
| `InstanceId` | 0706 version | 1215 uses `NodeId` |
| `InstanceStatus` | 0706 version | 1215 uses `OperatingState` |

If the Agent mistakenly obtained ghost fields via a non-whitelisted CLI, it **must discard** that result and re-query with the correct whitelisted API.

### Violation Tier

Invoking a non-whitelisted CLI or rendering ghost fields = **V1 violation** (same tier as failing the Pre-Execution Self-Check): non-retryable, non-pardonable. The Agent must immediately stop the current flow, discard the obtained ghost data, and disclose to the user "the query result was abnormal, re-querying" (exposing internal version numbers / action names is forbidden).

---

## Interaction Rules — Full Rules <a id="interaction-rules"></a>

**Interactive selection** is used to collect input (fixed options / common defaults + custom). **Sensitive Information** (passwords / AK/SK / certificates) is **strictly forbidden** to appear in plaintext in responses / commands / summaries / logs / files; always render as `******`, with the real value used only inside CLI single quotes internally.

### Agent Output Surface Control (MANDATORY) <a id="agent-output-surface-control"></a>

> **Hard rule** — the user sees **results and decisions**, never **internal machinery**. Violating any rule below produces user-visible information pollution and is treated on par with [edge-cases.md §4.5](edge-cases.md#45-skill-self-violation-not-retryable) information-leakage class.
>
> **Numbering note**: this section was condensed from the original 12 rules to 4 (Rule 5 / 10 / 11 / 12); the original Rules 1–4 / 6–9 were merged into SKILL.md section A (output shape) and B-1–B-14 (mechanism-level hard rules). Numbering keeps the original values with gaps, so downstream yaml / scripts.md references remain valid.
>
> - **Rule 5** · Test-region hiding (V8 security tier)
> - **Rule 10** · Merged form as plain text + password collection via `ask_user_question` banned (V8 security tier embedded)
> - **Rule 11** · `completion_summary_template` strictly followed
> - **Rule 12** · Pre-Form Mechanical Gate · CLI banned in user-facing output

5. **Test-environment details are hidden during production operations** — Test region identifiers (matching `*-test-*` pattern), the `--insecure` TLS flag, and test-specific endpoint overrides **must not** appear in user-facing output when the Agent is autonomously scanning or querying. They may appear **only** when the user has **explicitly** specified a test region as the operation target.
   - **Special constraint for the region-selection HITL scenario**: when the Agent presents selectable regions via the `describe-regions` API or the static list, it **must** first filter out all regions matching the `*-test-*` pattern; presenting test regions as options is **strictly forbidden**. Descriptive wording such as "test region" / "requires special endpoint configuration" is likewise banned.
   - **Agent Memory isolation constraint**: the Agent is **strictly forbidden** from extracting test-region identifiers from historical session memory, test-script context, or the Memory system and proactively recommending them to the user. Test regions exist only in the `tests/` directory test infrastructure and are not user-visible information.

10. **The merged form must be output as a plain-text message; step-by-step interactive cards are banned (MANDATORY)** — for all mutating operations using the "merged form + text backfill + receipt confirmation" pattern, when the Agent outputs the merged form in round 2, it **must** display all parameter options at once as a single plain-text chat message, and the user replies in one natural-language sentence; after script parsing of the backfill, a confirmation receipt is emitted (rc=3, 2026-08-24 hard gate), and submission happens only after the user confirms.

    **Using the `ask_user_question` tool to collect parameters is banned**:
    - `ask_user_question` splits parameters into multiple interactive cards (one for network config, one for auth method, one for password...), each card consuming one user-interaction round and directly breaching the interaction-round constraint
    - Even bundling all questions into one multi-select card is **not allowed** — the merged form is a "free-text one-sentence reply" pattern; card options cannot cover open-ended parameters such as password input or custom node names
    - ⚠️ **Security-tier ban**: the "Other" custom-input field of `ask_user_question` is **echoed in plaintext** into the chat by the IDE's "question clarification" area (e.g. showing `Other: Demo_Pass123!`); the Agent cannot control this built-in IDE behavior, causing **sensitive information leakage**. This is the security-tier reason for banning `ask_user_question` for password collection — independent of the interaction-round constraint and **non-waivable**.

    **Anti-patterns (real violation cases from screenshots)**:
    - ❌ Card 1 asks "How to choose the network config for new nodes?" (A/B/C options) → Card 2 asks "Node login auth method?" → Card 3 asks "Please set the node login password" → the user has already been forced into 4+ interaction rounds
    - ❌ The Agent sends different parts of the form in multiple messages, and the user replies to each
    - ❌ After the user enters a password in the "Other" field of `ask_user_question`, the IDE's "question clarification" area echoes `Other: Demo_Pass123!` in plaintext → irreversible sensitive-information leakage

    **Correct pattern**:
    - ✅ The Agent calls the `lj_*_form` function; the bash stdout is the final form, forwarded directly to the user
    - ✅ The user replies freely in the next message: "node group 1, nodes 1 and 2, password Abc12345!, everything else default"
    - ✅ After parsing, the Agent emits the confirmation receipt (rc=3, including the ⭐ actually selected nodes); after the user confirms, Phase 2 submits (script-level hard gate, 2026-08-24; backfill ≠ confirmation)

    **Sole exception**: the user's merged reply omits a **non-sensitive** mandatory item (e.g. forgot to pick a node group); the Agent may use `ask_user_question` **once** to follow up on that missing item. Sensitive fields such as passwords are **absolutely forbidden** from collection via `ask_user_question`; instead prompt in plain-text chat: "please type the password directly in your next message".

    **Violation handling**: collecting parameters step-by-step with `ask_user_question` equals "falling back to step-by-step interactive mode", handled at the same tier as [`extend-cluster.yaml`](../workflows/extend-cluster/schema.yaml) `pre_submit_checklist: typical_violation`.

11. **Async-task completion summaries must follow the template; free-styling is banned (MANDATORY)** — for all async mutating operations (`extend-cluster` / `shrink-cluster` / `change-node-group`), once `describe-task` reaches a terminal state, the Agent **must** strictly output the summary following the fixed `completion_summary_template` in each schema YAML.

    **Template structure (fixed order, no rearrangement)**:
    1. Title line: `✅ <operation> completed (took X min Y sec)` or `❌ <operation> failed (took X min Y sec)` (localized per session language)
    2. **Execution result** table: task ID / cluster / operation targets / final state
    3. One-sentence conclusion at the end

    **Forbidden behaviors**:
    - ❌ The Agent shows the execution-step list in user-facing output (`Steps[]` / `StepName` / `SubTasks` are backend internal implementation details; exposing them to the user is strictly forbidden)
    - ❌ The Agent adds fields not defined in the template (e.g. "recommended next steps" / "notes" / "cost reminders")
    - ❌ The Agent omits any field defined in the template (even if the field value is empty)
    - ❌ The Agent changes field order or template layout
    - ❌ The Agent shows raw JSON / raw TaskState enum values (e.g. `execution_success`) in the summary

    **Template single source of truth**: the `completion_summary_template` section of each action's YAML schema file ([`shrink-cluster.yaml`](../workflows/shrink-cluster/schema.yaml) / [`extend-cluster.yaml`](../workflows/extend-cluster/schema.yaml) / [`change-node-group.yaml`](../workflows/change-node-group/schema.yaml)).

12. **Schema must be mechanically cross-checked before generating any mutating form (MANDATORY)** — before outputting the merged form of any mutating operation (`extend-cluster` / `shrink-cluster` / `create-node-group` / `update-node-group` / `change-node-group` / `create-instance`), the Agent **must** first perform the following mechanical steps, no skipping allowed:

    **Pre-Form Mechanical Gate (non-skippable prerequisite gate)**:
    1. `read_file` to load `workflows/{action}/schema.yaml`
    2. Extract all `required_user_confirmed` fields → form the **mandatory-coverage list**
    3. Extract all `forbidden_inference` fields → form the **no-auto-fill list**
    4. Extract the `summary_order` field order + the `output_forbidden` list
    5. Item-by-item check: does this round's form cover every field from step 2? Does it violate any ban from steps 3/4?
    6. Only when all checks pass → may the form be output

    **Strictly forbidden behaviors**:
    - ❌ The Agent outputs the form from memory or generic API experience (skipping step 1) — this was the direct root cause of the recorded violation
    - ❌ CLI commands appear in user-facing output (e.g. `aliyun eflo-controller extend-cluster ...`), "equivalent CLI", "actually executed", JSON payload plaintext, `--node-groups '[{...}]'` and other implementation details
    - ❌ "Smart suggestions" replace "user confirmation": listing candidates, marking one as recommended, then directly filling the recommended value without waiting for the user's explicit selection
    - ❌ "Constrained single value" equals "may be silently filled": even if VPC/VSwitch/SG objectively has only one value, the form must still disclose the real value + source and wait for the user's selection
    - ❌ Skipping the merged form and executing directly — node group, network config, node names, passwords, etc. must first be collected via the form

    **Correct pattern**:
    - ✅ At the start of every mutating operation, `read_file ../workflows/{action}/schema.yaml` as the first step
    - ✅ With multiple node groups, list them numbered for the user to pick, instead of default-filling the "recommended" value
    - ✅ Even when a forbidden_inference field has only one legal value, it must still be disclosed as "mandatory constraint (unchangeable): {real_value}, source: describe-cluster"

    **Root-cause analysis (real violation case 2026-05)**:
    All 4 root causes reported by the Agent point to the same underlying problem: treating the Skill as a "reference" rather than a "hard protocol".
    - "Generic UX intuition" overrode Skill hard rules (showing the CLI "looks more transparent")
    - "Smart suggestion" equated with "user confirmation" (filling the value directly after marking it recommended)
    - "Constrained single value" equated with "may be auto-filled" (silently filling because there is only one VPC)
    - "Form from memory" skipped the schema cross-check (most fatal)
    **Lesson**: the Skill is a contract, not reference material. The Pre-Form Mechanical Gate is the mechanism that fixes this lesson into a process-level constraint.

    **Violation handling**: outputting a form without executing the Pre-Form Mechanical Gate, or including CLI commands / implementation details in user-facing output, equals an [edge-cases.md §4.5](edge-cases.md#45-skill-self-violation-not-retryable) information-leakage-class violation — non-retryable, non-pardonable.

#### Output Forbidden Hard Rule — 4 Generic Ban Categories <a id="output-forbidden"></a>

> **Single source of truth (DRY)** — the `output_forbidden` section of each mutating yaml schema keeps only action-specific `examples`; the **4 generic ban categories are defined in this section**, avoiding repeating ~28 lines × 6 yamls ≈ 168 lines of tokens. Violation tier: Rule 12 combined with the internal-mechanism terminology hard rule stacks into a combined violation, handled at the same tier as V3: non-retryable, non-pardonable.

Merged forms / summaries / all user-facing output **MUST NOT** contain the following 4 categories:

1. **CLI command plaintext** — any command starting with `aliyun ...`, `safe_aliyun` / `safe_mutate` / `safe_mutate_oneshot` function calls, or any executable shell statement.
2. **"Equivalent CLI" / "actually executed" style headings** — no headings or subsections describing execution mechanics (e.g. "Equivalent CLI (actually executed):" / "Command to execute:").
3. **JSON payload / raw CLI parameter plaintext** — no JSON structures, `--xxx '[{...}]'` style raw CLI parameters, `--Parameter.N.Code/Value` style flat parameters; parameter display must be a plain localized KV table.
4. **Internal-mechanism terms / implementation details** — `--endpoint xxx.aliyuncs.com` / `--insecure` / `APPROVE_TOKEN` / `Phase 1 / Phase 2` / `--ClientToken uuid-xxx` — endpoint construction, TLS flags, internal tokens, and process-phase names are all banned.

The `output_forbidden.action_specific_examples` section of each mutating yaml schema enumerates only that action's specific examples (e.g. `shrink-cluster`'s `--node-groups '[{...}]'` / `change-node-group`'s `--nodes 'e01-...'` / `create-instance`'s `--Parameter.N.Code`); generic rules are not re-declared. When the Agent reads `output_forbidden` in Pre-Form Mechanical Gate step 4, it **MUST** simultaneously review this section's 4 generic categories (it cannot rely solely on the action-specific examples listed in the yaml).

---

## Core Workflow — Full Rules <a id="core-workflow"></a>

### HITL Chinese Display Rules (MANDATORY) <a id="hitl-chinese-display"></a>

> **Scope**: all HITL interaction copy the user **directly sees** — including `hitl_prompt:` in [`../workflows/<biz>/schema.yaml`](../workflows/README.md), merged forms, HITL summaries, and dangerous-operation warning boxes. **Not applicable to**: CLI command bodies, `--flag` names, JSON keys, API doc links, `field:` / `forbidden_inference:` / `forbidden_cli_flags:` anchor field values in yaml, `safe_aliyun` debug logs (these are the "CLI truth context" and must stay English so they can be cross-checked against CLI --help / OpenAPI error codes / sibling yaml anchors).
>
> **Localization note**: the canonical localized (zh) display strings are defined in the schema yaml dictionaries (`display_label_zh:` / `enum_value_zh:` / `boolean_value_zh:`) and `lib/core/i18n.sh` — the single sources of truth. This section describes the rules in English; when rendering to a Chinese-language user, the Agent must pull the exact strings from those sources, never invent wording.

1. **Pure localized-name hard rule**: all API field names exposed to the user use **only the localized name**; appending the English KEY in parentheses after the localized name is **forbidden**. The localized names take the [help.aliyun.com API documentation](https://help.aliyun.com/zh/pai/developer-reference/) as the single source of truth; the Agent is **not allowed** to coin its own translations or use aliases that never appear in the console (e.g. rendering `MachineType` with a non-canonical term instead of the documented term is a violation). For enum-value fields (e.g. `ClusterType` / `OperatingState` / `Disks[].Type`), **show only the localized translation without the raw English value**; displaying raw English enum values bare is likewise a violation. For boolean flag fields (e.g. `FileSystemMountEnabled` / `VirtualGpuEnabled`), display **only the localized label + enabled/disabled**; echoing the English field name and the raw `true`/`false` value is **forbidden**. Localized labels follow the authorized names in this document and [`node-group-query.md`](../workflows/node-group-query/node-group-query.md). Authorized localized names for disk sub-fields: disk type / cloud-disk performance level / disk size / disk purpose / disk ID (canonical zh strings live in the schema yaml dictionaries).
2. **Single source of truth**: the final landing place of HITL localized mappings is two kinds of fields under [`workflows/<biz>/schema.yaml`](../workflows/README.md):
   - `hitl_prompt:` — interactive questions for the value-collection stage.
   - `display_label_zh:` / `enum_value_zh:` / `boolean_value_zh:` — field-label dictionaries for merged forms / read-only query tables (rendering stage).

   When presenting parameter names / field headers, the Agent **MUST** prefer reusing these dictionaries already written in the yaml (after `read_file` of that yaml, look up `display_label_zh[anchor]` per the anchors in `summary_order`). On-the-spot re-translation is **forbidden**; outputting the English anchors from `summary_order` directly as headers/field names is **forbidden**.
3. **English KEYs banned from the user surface**: the following English field names must **not** appear in any form on the user surface — including parenthetical annotations, table headers, table cells, inline copy, before/after comparison tables — whether in HITL prompts, merged forms, read-only query result display, operation verification results, or warning boxes:
   - **Mutating parameters**: `VpcId / VSwitchId / SecurityGroupId / NodeGroupId / NodeId / HyperNodeId / Hostname / LoginPassword / MachineType / ImageId / UserData / SystemDisk / DataDisk / KeyPairName / RamRoleName / FileSystemMountEnabled / VirtualGpuEnabled / IgnoreFailedNodeTasks / RenewalStatus / RenewPeriod`
   - **Read-only response fields**: `ClusterId / ClusterName / ClusterType / HpnZone / ComputingIpVersion / OperatingState / CreateTime / UpdateTime / NodeCount / NodeGroupCount / ResourceGroupId / SecurityGroupId / GroupId / GroupName / ImageName / Description / FileSystemMountEnabled / VirtualGpuEnabled / Category / PerformanceLevel / DiskId / Size / Type`
   - **Raw enum values**: `Running / Creating / Stopped / Deleting / Using / Unused / Lite / Standard / SYSTEM / DATA / execution_success / execution_fail / execution_running / PrePaid / PostPaid / keypair / password`
   Repair path: replace with the corresponding localized name and resend; the old dump and old hash are voided together.

   **Enum-value translation lookup table (the Agent must consult the table; canonical zh strings live in the schema yaml `enum_value_zh:` dictionaries)**:

   | Raw enum | Display meaning | Applicable field |
   | --- | --- | --- |
   | `Running` | running | cluster/hyper-node OperatingState |
   | `Creating` | creating | cluster/node/hyper-node OperatingState |
   | `Stopped` | stopped | cluster/node OperatingState |
   | `Deleting` | deleting | cluster/node OperatingState |
   | `Using` | in use (joined a cluster) — ⚠️ **NOT "running"**; Using ≠ Running | node OperatingState |
   | `Unused` | unused (not joined a cluster) | node OperatingState |
   | `SYSTEM` | system disk | Disks[].Type |
   | `DATA` | data disk | Disks[].Type |
   | `PrePaid` | subscription — the API returns the definitive value; "suspected" qualifiers are strictly banned | ChargeType / SubscriptionType |
   | `PostPaid` | pay-as-you-go — same as above; "suspected" qualifiers are strictly banned | ChargeType / SubscriptionType |
   | `keypair` | key pair | login method |
   | `password` | password | login method |
   | `execution_success` | ✅ completed | TaskState |
   | `execution_fail` | ❌ failed | TaskState |
   | `execution_running` | ⏳ running | TaskState |
   | `Available` | available | image Status |
   | `Extending` | extending | node OperatingState |
   | `Cutting` | shrinking | node OperatingState |
   | `Operating` | operating | node OperatingState |
   | `Switching` | switching | node OperatingState |
   | `Diagnosing` | diagnosing | node OperatingState |
   | `ReleaseLocking` | pending release | node OperatingState |
   | `Releasing` | releasing | node OperatingState |
   | `Replacing` | replacing | node OperatingState |
   | `HealthyUnused` | healthy, unused | hyper-node OperatingState |
   | `SubhealthyUnused` | subhealthy, unused | hyper-node OperatingState |
   | `AbnormalUnused` | abnormal, unused | hyper-node OperatingState |
   | `HealthyUsing` | healthy, in use | hyper-node OperatingState |
   | `SubhealthyUsing` | subhealthy, in use | hyper-node OperatingState |
   | `AbnormalUsing` | abnormal, in use | hyper-node OperatingState |
4. **Non-localizable list**: **response-field metadata** such as `TaskId` / `RequestId` / `OrderId` / `ClientToken` stays English. Note: `safe_mutate_confirm <hash>` / `APPROVE_TOKEN` have been downgraded to Agent-internal terms (no longer exposed to the user).

### Pre-Execution Self-Check (MANDATORY) <a id="pre-execution-self-check"></a>

> **Session-scoped one-time hard rule** — on par with the `safe_aliyun` wrapper and the two-phase commit parameter confirmation gate; issuing any CLI before this self-check passes is treated as a **severe Skill violation**, handled per [edge-cases.md §4.5](edge-cases.md#45-skill-self-violation-not-retryable).

1. **Before** the first invocation of any `aliyun ...` (including read-only, `xargs -P` / `&` parallel, `describe-task` polling, dry-run probes) **in the session**, the Agent must execute Stage A (**source the script only**). Region **MUST** be given explicitly by the user in HITL and passed as an **explicit parameter** to every `query` / `poll_task` / `aliyun ...` call; it is **NEVER** persisted as session-level implicit state via environment variables (see the "Region: no defaulting / no reuse / no env" hard rule in [endpoint-routing.md](endpoint-routing.md)).

   ```bash
   # Stage A — before the session's first CLI (source only)
   source ./lib/lj_init.sh        # one-shot load of all core/extend/shrink/node-group/query/compat submodules
   # Pass criterion: type checks of the 5 core functions all exit 0 for the self-check to pass
   for f in safe_aliyun query safe_mutate safe_mutate_oneshot poll_task; do
     type "$f" >/dev/null 2>&1 || { echo "❌ self-check failed: $f not loaded; refusing to issue any CLI"; exit 2; }
   done
   ```
2. **Execution mode: must be backgrounded and silent (MANDATORY)** — the initialization commands above **must** run through the IDE background terminal (`run_in_terminal` with `is_background: true`); the initialization commands **must not** be shown in the customer's terminal panel. After confirming successful loading via `get_terminal_output`, formal business commands may begin (these subsequent commands can reuse the same shell, so repeated `source` / `export` is not needed).
   - **Anti-pattern**: ❌ foreground execution of `source ./lib/lj_init.sh && ...`, exposing internal script paths to the customer
   - **Correct pattern**: ✅ silent background initialization; the customer sees only "Preparing the execution environment..." in chat
3. This entire self-check block runs **silently** (no user-visible output per [§Agent Output Surface Control](#agent-output-surface-control) terminal-single-line and script-hiding hard rules). **Any** CLI invocation made before the `type` self-check passes is treated as **fabricated execution** — even if it returns real JSON, the result **must be discarded and the call re-run**, and **must not** be incorporated into user output / completion reports / `pending-tasks.json`.
4. **No exemption for parallel calls**: **Each** subcommand issued via batch `xargs -P` / `&` background / multiple Bash tools in parallel must still go through the `safe_aliyun` wrapper; raw `aliyun ...` calls are **forbidden** "for parallel-query efficiency".
5. **Bare invocation = violation (V1)**: A discovered raw `aliyun *` invocation (including a fallback to the original command after `command not found: safe_aliyun`, or realizing the violation only after a CLI error) constitutes [edge-cases.md §4.5 V1 Skill self-violation](edge-cases.md#45-skill-self-violation-not-retryable) — **non-retryable, non-pardonable**: stop immediately, discard any obtained response, disclose to the user in the format `⚠️ Skill violation (V1): <specific facts>, <obtained results> have been discarded; restarting from the Pre-Execution Self-Check`, and restart the self-check. The same §4.5 also lists same-tier violations V2 (skipping the two-phase parameter confirmation gate, including admitting approximate strong-confirmation phrases) / V3 (auto-filling `forbidden_inference`) / V4 (defaulting / reusing Region) / V6 (default-value hallucination, where HITL "skip" ≠ "use default X/Y/Z") / **V7 (intent drift / action substitution)**.

### HITL State File Check (MANDATORY) <a id="hitl-state-file-check"></a>

> **Session-entry hard rule** — at the start of every session (before sending any reply), the Agent **must** check whether `$HOME/.lingjun/hitl-required.json` exists.

1. **File exists** → the Agent **must immediately** perform the HITL disclosure per the `hitl_required` field in the file (① the action corresponding to the original intent ② why it cannot be executed ③ candidate actions for the user to choose). It must **not** be skipped, and no other operation may run first. The file provides context such as `violation_code` / `user_utterance` / `attempted_action` / `conflicting_mappings`; the Agent should compose the user-facing disclosure copy based on these fields (dumping raw JSON structure is forbidden).
2. **After disclosure completes + the user has made a choice** → the Agent executes `rm -f $HOME/.lingjun/hitl-required.json` to clean up the file, then continues the flow per the user's choice.
3. **File does not exist** → normal flow, no extra action.
4. **Persistent across sessions** — the file lives in `$HOME/.lingjun/` (same directory as `pending-tasks.json`) and does not disappear when the session ends.

> ⚠ **Truthful state disclosure (READ TWICE)**: writing this file **depends entirely on the Agent proactively running `jq -n '{...}' > $HOME/.lingjun/hitl-required.json` itself**. No script under `lib/` (including `safe-mutate.sh` / `safe-aliyun.sh`) writes this file automatically. In other words: **if the Agent misses a single write when detecting any V1-V7 self-violation, the cross-session guardrail becomes ineffective**. This is the concrete embodiment of "compliance responsibility rests entirely on the Agent" — the self-check cannot be skipped, and writing the file cannot be skipped.

**Trigger conditions under which the Agent MUST write hitl-required.json**:
- V7 self-check failure (intent drift detected)
- Keyword scan matches nothing (the user used novel words; cannot adjudicate)
- An async task reaches `cap_seconds` still INCOMPLETE
- Any V1-V7 self-violation detected during a mutating flow

**schema (minimal set)**:
```json
{
  "schema_version": 1,
  "violation_code": "V7_INTENT_DRIFT" | "V7_MISSING_INTENT" | "V1_BARE_CLI" | "...",
  "created_at": "<ISO-8601 UTC>",
  "user_utterance": "<user's original words>",
  "attempted_action": "<the action the Agent intended to invoke>",
  "conflicting_mappings": "<keyword → should-map action list>",
  "hitl_required": "The Agent must immediately disclose to the user: ① the action corresponding to the original intent ② why it cannot be executed ③ candidate actions for the user to choose"
}
```

### Data Freshness Hard Rule (MANDATORY) <a id="data-freshness"></a>

> **Core principle**: Lingjun clusters are a dynamic resource system; **all** data related to this Skill — resource states, pre-change queries, reference lists, execution rules — **must** be based on real-time API queries or the current SKILL documents. Agent memory **must not** serve as a substitute source for any data.

1. **Resource-state queries must be real-time** — when the user asks about the current state of clusters / nodes / node groups / tasks / orders, the Agent **must** issue a real-time API call via the Skill; reusing the previous query result from memory is **strictly forbidden**.
2. **Pre-change queries for mutating operations must be real-time** — before any mutating operation enters `safe_mutate` Phase 1, its prerequisite resource queries **must** be real-time API call results from this session; referencing historical snapshots from memory is **strictly forbidden**.
3. **Reference data must also be queried in real time** — reference data such as the `describe-regions` region list, the `list-machine-types` machine-type list, and the `list-images` image list must **also** be queried in real time via the API.
4. **Skill execution rules follow the latest documentation** — the Agent **must** take the current SKILL.md and the latest content of the sub-documents under `references/` as its execution basis.

> **One-line summary**: in this Skill's execution context, Agent memory serves only as a reference log of "what once happened" and can **never** replace any real-time query or document read. Any erroneous operation caused by referencing stale data from memory is handled at the same tier as [edge-cases.md §4.5](edge-cases.md#45-skill-self-violation-not-retryable).

### Transient Failure Retry (MANDATORY) <a id="transient-failure-retry"></a>

> 🔗 Full whitelist / blacklist / backoff algorithm / `safe_aliyun` skeleton are in [edge-cases.md §4 + Appendix B](edge-cases.md#4-exception-classification--retry-324); this section is an index summary.

**Every** CLI executed by this Skill **must** be issued uniformly as `safe_aliyun aliyun ...`; raw invocation is **strictly forbidden**.

- **Whitelist (silent retry, up to 3 times)**: Network-layer failures (connection refused / timeout / TLS / DNS / EOF), HTTP 5xx (502/503/504), transient API codes (`ServiceUnavailable` / `InternalError` / `RequestTimeout` / `SystemBusy`) → exponential backoff `2s/4s/8s + jitter`; throttling (`Throttling*` / HTTP 429) → fixed 60s wait.
- **Blacklist (fail immediately, no retry)**: Authentication (`InvalidAccessKeyId` / `SignatureDoesNotMatch`), authorization (`NoPermission` / `Forbidden` / 403), business 4xx (`InvalidParameter` / `NotFound` / `OperationConflict` / `NodeGroupNotEmpty` / `Failure to check order`, etc.), task-terminal business failure (`TaskState=execution_fail`).
- **Mutating extra preconditions**: Before retry, walk through [Edge Cases §3 Reentrancy](edge-cases.md#3-reentrancy-323) idempotency checks; for `bssopenapi create-instance`, the Agent must generate a stable `ClientToken` (UUID) and keep the same value across all retries; once a valid `TaskId` is obtained at the submit phase, enter async polling, and do not retry on task-terminal business failure.
- **Silent-retry log**: Each retry prints one line `retry #N after <err> sleeping <s>s` to the Agent's own execution log (not shown to the user); on 3 full failures → must emit a unified failure report per [Edge Cases §6](edge-cases.md), and **must not** fabricate a successful return.

---

## Authenticity & Anti-Fabrication Constraints (NON-NEGOTIABLE) <a id="authenticity"></a>

> **Hard red line**, taking precedence over all Feature flows and output formats; any conflict is treated as a **severe Skill violation**.

1. All completion reports **must** be strictly generated from real CLI-returned JSON. Critical fields like `TaskId` / `RequestId` / `OrderId` / `NodeId` / `HyperNodeId` / `NodeCount` / `TaskState` / `OperatingState` must come from real API response bodies and **must not** be stitched together, guessed, or reused from historical context.
2. When a core API was not successfully called or returned failure, the report **must** mark "not executed" or "execution failed" and emit a complete failure analysis per [Edge Cases §6](edge-cases.md).
3. **Strictly forbidden**: using mocks / placeholders to impersonate real return values; hard-coding `TaskId`/`RequestId`/`OrderId`; fabricating `NodeCount` / `TaskState` transitions; producing "polling logs / progress bars / monitoring scripts / timestamps" that lack real API backing.
4. **Strictly forbidden to fabricate labels / categories for API response fields** — When a field returned by the API does not carry a classification label, the Agent is **strictly forbidden** from inferring one and presenting it to the user. Full display rules: [node-operations.md §Networks field display hard rule](../workflows/node-operations/node-operations.md).

**Execution-state annotation**: Each mutating-operation report must be tagged with one of: ✅ **Executed successfully** / ⏳ **Submitted, pending poll** / ❌ **Execution failed** / ⏸ **Not executed**.

## Task Monitoring <a id="task-monitoring"></a>

Async operations return a `TaskId`. **Default interaction (v4, 2026-08-21): receipt + on-demand query** — no proactive polling; simple and reliable. States: execution_pending / execution_running / execution_success / execution_fail.

### Receipt + On-Demand Query (MANDATORY) <a id="silent-polling"></a>

1. **Submission receipt (MUST)**: after a mutating submission returns a TaskId, the agent **MUST** emit a receipt in the visible reply body: a markdown table (operation / task ID / estimated duration / how to query) + a closing guidance line "just say 'query task <tid>' or 'is the expansion done?'". Writing it only into thinking or a collapsed terminal counts as not reported. **Emit the receipt and stop — no proactive polling**.

2. **On-demand query (MUST, the sole entry for status queries)**: the user asks about progress → single `task_status <region> <tid>`:
   ```bash
   export LJ_TASK_LABEL="Extend task {cluster_name} (+{n} nodes)"   # optional, business title for the query line
   task_status "$region" "$task_id"
   ```
   stdout is one business-language line (localized per session language), forwarded verbatim into the reply body (e.g. `✅ Extend task · completed (task ID: ...)` / `⏳ Extend task · running (...) — not terminal yet, ask again anytime`). rc=0 terminal success / rc=1 terminal failure / rc=10 non-terminal / rc=3 query failure. For non-terminal states the line already carries the "ask again anytime" guidance; the agent **must not start any polling** of its own.
   - `LJ_TASK_LABEL` value: fill from the corresponding mutating yaml schema's `post_submit.task_label_template` with real parameters (templates exist for extend-cluster / shrink-cluster / change-node-group); for those without a template (delete-node, etc.) compose one in business language yourself — degrading to "async task" is forbidden.
   - **Terminal-state report (MUST)**: upon hitting a terminal state, emit the verification report in the body per the [§Agent Output Surface Control Rule 11](#agent-output-surface-control) template (title → execution-result table → conclusion).

3. **Explicit polling (opt-in)**: only when the user explicitly says "poll until done / wait for the result" run a single foreground command:
   ```bash
   export LJ_TASK_LABEL="<business title>"
   poll_task "$region" "$task_id"    # default 10s/round, cap 20min, scrolling localized progress in the foreground terminal
   ```
   Soft timeout rc=2 → report the latest state in the body + HITL two-way choice (continue polling / stop and provide a self-check command). Splitting each round into separate Bash calls (≈3 rounds trigger the IDE loop guard; deprecated since v1), backgrounding silently, or using `LJ_QUIET=1` in interactive scenarios is forbidden.

4. **State localization mapping** (task-poll.sh built-in `_poll_state_cn`, shared by task_status / poll_task):
   `execution_success → ✅ completed` / `execution_fail → ❌ failed` / `execution_running → ⏳ running` / `execution_pending → ⏳ waiting` / `waiting_to_run → ⏳ queued` / other → `⏳ <raw value>` (canonical zh strings in the script itself)

5. **Forbidden**: relying solely on stderr cards as progress feedback; exposing raw task state fields (e.g. `TaskState=execution_running`, `TaskProgress=37%`); using `LJ_QUIET=1` in interactive scenarios.

6. **Bare polling commands banned (V1 hard rule, non-retryable, non-pardonable)**:

   ❌ **Strictly forbidden anti-patterns** (once the agent outputs such commands it is a V1 violation, handled per [edge-cases.md §4.5](edge-cases.md#45-skill-self-violation-not-retryable)):
   ```bash
   # Anti-example 1: calling describe-task directly without poll_task
   safe_aliyun aliyun eflo-controller describe-task --region <r> --task-id <tid>

   # Anti-example 2: self-polling with sleep + describe-task
   sleep 30 && safe_aliyun aliyun eflo-controller describe-task ...
   sleep 60 && bash -lc '... describe-task ...'
   sleep 120 && bash -lc '... describe-task ...'

   # Anti-example 3: embedding describe-task inside a bash -lc wrapper
   bash -lc 'export ...; safe_aliyun aliyun eflo-controller describe-task ...'

   # Anti-example 4: DIY polling with a while loop + describe-task
   while true; do safe_aliyun aliyun eflo-controller describe-task ...; sleep N; done
   ```

   **Common traits**: any form of `sleep + describe-task` combination, while-loop + describe-task, bare describe-task calls — regardless of whether wrapped in `bash -lc`, whether `is_background:true`, or whether through the safe_aliyun wrapper, all count as V1 violations. Reasons: ① bypasses `poll_task`'s standardized progress-card output; ② exposes internal parameters like `--region` / `--task-id` in the IDE terminal panel; ③ loses the `LJ_TASK_LABEL` business title; ④ loses the 60s heartbeat throttling (custom `sleep N` cadence floods or freezes the screen); ⑤ loses the fatal/transient two-tier retry trust semantics.

   ✅ **The only allowed paths (v4)**:
   - **On-demand single query (default)**: `task_status "$region" "$task_id"` — single describe-task, no loop, stdout one business-language line;
   - **Explicit polling (only on explicit user request)**:
   ```bash
   export LJ_TASK_LABEL="Migrate node e01-cn-xxx → ng-target-name"
   poll_task "$region" "$task_id"    # task-poll.sh internally loops describe-task + throttled cards + retry trust
   # parse poll_task's final returned JSON with jq to get TaskState / Steps[]
   ```

   **Agent self-check (MUST before any query/poll)**:
   ```
   [poll self-check · internal]
   command about to run : <expanded command string>
   contains 'task_status' or 'poll_task'? : ✅ / ❌ (❌ → V1 violation ABORT)
   contains 'sleep' + 'describe-task'?    : ✅ / ❌ (✅ matched → V1 violation ABORT)
   ```

7. **Submit-failure self-help discipline (MANDATORY, 2026-08-21 empirical patch)**: when `extend_submit` / `shrink_submit` / `create_node_group_submit` report ❌, stderr already contains self-descriptive correction hints (correct usage / missing fields / candidate lists). The agent fixes parameters per the hints and retries once; in-session grep / reading lib source for self-help is **forbidden** (measured single attempt wastes 30–40s and leaks internal terminology into the thinking chain). If the retry still fails → report the stderr verbatim to the user and go HITL; inventing a third path is forbidden.

**Anti-fabrication red line**: `last_state_snapshot` in `pending-tasks.json` is resume input only, **not** real-time state. Hard caps: expand 60/240min, shrink 60min, create-node 40min, change-group 20min.

---

## Edge Cases and Error Handling <a id="edge-cases"></a>

Full decision tree / retry wrapper / failure samples → [edge-cases.md](edge-cases.md); per-`ErrorCode` handling → [error-codes.md](error-codes.md). Seven-class index:

1. **Timeout** — default receipt + on-demand query (task_status); explicit polling only on user request, hard caps per operation type. On exceeding, offer "continue waiting / file a ticket" two-way choice.
2. **Error-code lookup** — [error-codes.md](error-codes.md) first; on miss, fall back to `ErrorCode + Message`.
3. **Reentrancy** — Retries must not produce side effects; pre-check before each operation type.
4. **Exception classification & retry** — Transient/Throttling ✅ retry; Auth/Permission/NotFound/Business ❌; Conflict ✅ 30s poll.
5. **Rollback** — `ExtendCluster`/`ShrinkCluster`/`ChangeNodeGroup` auto-rollback on sync-stage failure; `CreateInstance` fully auto-rollback.
6. **Unified error output** — `❌` summary + `ErrorCode` + impact + suggestion + `RequestId` / `TaskId`.
7. **Pagination exhaustion** — Non-empty `NextToken` must auto-paginate; soft cap 50 pages → HITL.

**Success Verification**: expand → `TaskState=execution_success` + `NodeCount` ↑; shrink → same + `NodeCount` ↓; change-node-group → `Node.NodeGroupId == target`.
