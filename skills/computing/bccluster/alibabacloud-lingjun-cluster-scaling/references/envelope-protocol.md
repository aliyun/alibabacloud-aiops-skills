# R2 Envelope Pass-Through Protocol

## User-Facing FAQ (not part of the protocol)

> The following is aimed at end users who use the widget; it does not affect the agent execution protocol.

**Q: What is the `[Widget interaction] {"__lj_b64":"..."}` that appears in the chat area after submitting?**

A: This is normal platform behavior. When you click "Submit" in the form, the platform shows the operation instruction as a message in the chat area. **Please send that message** — once the agent receives it, it starts executing the create/expand action.

**Q: Can this message be hidden?**

A: The platform's submit interface currently has no silent switch; the submit message is always visible. This is a platform limitation, not a skill design issue.

**Q: What is the encrypted content in the message?**

A: It is the base64-encoded operation parameters. The purpose of this wrapping is to ensure the agent mechanically passes the parameters through to script execution per the rules, without modifying them on its own.

---


> This document was extracted from SKILL.md; it describes the full recognition and execution protocol for Round 2 (user confirms submission).
> When R2 is triggered the agent **must** follow this protocol: zero parsing, zero confirmation, immediate execution.

---

## Core Principles

- Widget submission / text backfill = **user has confirmed**
- The only action allowed to the agent = **immediate single Bash** (decode + source + submit merged into one `&&` chain command)
- **Absolutely forbidden**: after decoding, printing JSON / echoing parameters / restating fields / second confirmation / asking the user / calling AskUserQuestion / printing "I will…" / "please confirm…" / "parameters are as follows…" / Reading any file / grepping code / re-calling form / re-rendering widget

---

## Pattern Recognition Rules

When a message matches any of the following patterns → user has confirmed → agent executes immediately:

### Pattern A (base64 widget)

**Trigger**: `[Widget interaction]` prefix + JSON contains an `__lj_b64` field

**Execution**:
```bash
# single && chain command (splitting into multiple Bash tool calls is forbidden)
printf '%s' '<__lj_b64 value>' | base64 --decode > /tmp/.lj-<route>-envelope.json && source "$LJ_SKILL_DIR/lib/lj_init.sh" && <submit function> /tmp/.lj-<route>-envelope.json
```

**action routing**:
| action | temp file | submit function |
|--------|-----------|-------------|
| extend-cluster | `/tmp/.lj-extend-envelope.json` | `extend_submit` |
| create-node-group | `/tmp/.lj-create-ng-envelope.json` | `create_node_group_submit` |

### Pattern B (plaintext widget compatibility)

**Trigger**: `[Widget interaction]` prefix + JSON does NOT contain `__lj_b64`

**Execution**: strip the 21-character prefix → write the JSON verbatim to the temp file → call the submit function

### Pattern C (text mode)

**Trigger**: `__LJ_EXEC__ extend-cluster` / `__LJ_EXEC__ create-node-group` prefix

**Execution**: cut the prefix → write the JSON verbatim to the temp file → call the submit function

### Backward Compatibility

If the whole message parses as JSON and `.action == "extend-cluster"` or `"create-node-group"` → write the entire segment to the temp file

---

## Submission Chain (detailed)

> Since 2026-08-20, R1 always uses a markdown text form (including Qoder IDE); widget rendering is banned;
> the Widget submission branches below exist only for legacy compatibility (backfill from historically opened widgets).

### extend-cluster

1. **R1**: agent calls `extend_form` → stdout is the markdown form, output verbatim (no more platform branching, no more `===EXTEND_MODE=widget===`)
2. **User submits**:
   - Text (the only active path): user fills in by hand → `__LJ_EXEC__ extend-cluster {JSON}` or natural-language backfill → `extend_submit --user-utterance`
   - Widget (legacy compatibility only): JS calls `ljSealEnvelope(env)` → base64 → `sendToAgent({__lj_b64:b64, action:"extend-cluster"}, {submit:true})`
3. **R2**: agent recognizes per Pattern → executes in a single Bash

### create-node-group

1. **R1**: agent calls `create_node_group_form` → stdout is the markdown form, output verbatim (no more platform branching, no more `===CREATE_NG_MODE=widget===`)
2. **User submits**:
   - Text (the only active path): user fills in by hand → `__LJ_EXEC__ create-node-group {JSON}`
   - Widget (legacy compatibility only): JS calls `ljSealEnvelope(env)` → base64 → `sendToAgent({__lj_b64:b64, action:"create-node-group"}, {submit:true})`
3. **R2**: agent recognizes per Pattern → executes in a single Bash

---

## Envelope Field Schema

### extend-cluster (v1)

| Category | Fields |
|------|------|
| Common | `v=1` / `action="extend-cluster"` / `region` / `clusterId` / `vpcId` / `vSwitchId` / `securityGroupId` / `path`(A\|B) |
| Multi-group mode | `nodeGroups: [{nodeGroupId, hostnames, freeNodeIds?, nodes?, loginPassword?, tags?}, ...]` |
| Per-node password | `nodeGroups[i].nodes[j].loginPassword` (Path A detail tab, per-node independent password) |
| Per-group password | `nodeGroups[i].loginPassword` (Path B or template tab, shared within the group) |
| Per-group tags | `nodeGroups[i].tags` (new format: `[{Key,Value},...]` array; old format: `"k=v,k=v"` string, submit.sh auto-detects) |
| Backward compatibility | top-level `loginPassword` / `tags` / `dataDisk` (used by non-multi_ng or old widgets) |
| Path A only | per-group `freeNodeIds` (array) |
| Path B only | `chargeType`(PrePaid\|PostPaid), PrePaid adds `period`/`autoRenew`, optional `vpcId`/`vSwitchId` |
| Optional | `userData` |

- Per element: `nodeGroupId`(required) + `hostnames[]`(required) + `freeNodeIds[]`(required for Path A)
- Optional `nodes?[]`: one item per node `{hostname, freeNodeId, dataDisk?, loginPassword?}`. Under Path A this overrides the group-level password for that node or configures an independent data disk
- Path B `amount` is derived automatically from each group's `hostnames.length`
- Backward compatibility: top-level `nodeGroupId`/`hostnames`/`freeNodeIds` and other fields still work; the bash side auto-wraps them into a single-element `nodeGroups[]`
- `dataDisk` format: `[{"Category":"cloud_essd","Size":500,"PerformanceLevel":"PL0","DeleteWithNode":true,"BurstingEnabled":true}]`
- Password priority chain: `nodes[j].loginPassword > nodeGroups[i].loginPassword > top-level loginPassword > null`
- NodeTag priority chain: `nodeGroups[i].tags > top-level tags > null`

### create-node-group (v1)

| Category | Fields |
|------|------|
| Required | `v=1` / `action="create-node-group"` / `region` / `clusterId` / `nodeGroupName` / `machineType` / `az` / `imageId` / `systemDisk`({Category,Size,PerformanceLevel}) |
| Optional | `loginPassword` / `keyPairName` / `ramRoleName` / `description` / `userData` / `fileSystemMountEnabled` / `virtualGpuEnabled` |
| Batch mode | `sharedLoginPassword` + `nodeGroups: [{nodeGroupName, machineType, az, imageId, systemDisk, ...}, ...]` |

---

## Forbidden Behavior List

| # | Forbidden |
|---|------|
| 1 | Decomposing envelope JSON fields and hand-assembling aliyun CLI parameters |
| 2 | LLM "re-confirming" parameters on its own |
| 3 | Re-calling form / re-rendering widget in R2 |
| 4 | Writing `qoder_show_widget` / `show_widget` inside bash (they do not exist in the shell) |
| 5 | Reading render.yaml / grepping functions / manually jq-reading /tmp/lj-*.json |
| 6 | Refusing to execute and asking the user to "confirm once more" |
| 7 | Splitting decode + source + submit into multiple Bash tool calls (must be a single `&&` chain command; splitting makes the user click "Run in Terminal" multiple times + terminal reuse causes FUNCNEST stack overflow) |

---

## Security Note

- `loginPassword` enters the chat history along with the envelope; remind the user to use a one-time password or rotate it after the node comes online
