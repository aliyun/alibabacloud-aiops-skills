# `operate-node --operation-parameters` Schema & Validation

Backend shape (`OperateNodeBaseRequest.OperationParameters` in [pkg/pai-resource-service/model/node/node.go](file:///Users/shining/Projects/pai-mono/pkg/pai-resource-service/model/node/node.go)):

```json
{
  "DrainParameters":    { "PodNames": ["..."], "PodFromSubProducts": ["DLC"] },
  "CordonParameters":   { "QuotaId": "", "WorkspaceId": "", "Comment": "" },
  "UncordonParameters": { "QuotaId": "", "WorkspaceId": "" }
}
```

Only the sub-object matching the chosen `--operation` is read; omit the others.

## CordonParameters / UncordonParameters

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `QuotaId` | string | paired with `WorkspaceId` | Scope. MUST be set together with `WorkspaceId`. |
| `WorkspaceId` | string | paired with `QuotaId` | Scope. MUST be set together with `QuotaId`. |
| `Comment` | string | optional (Cordon only) | Free-text reason recorded in audit event. |

**Pairing rule** (backend-enforced): `QuotaId` and `WorkspaceId` MUST be provided **together** or **both omitted**. One-without-the-other is rejected with `"both quota id and workspace id should be provided"`.

> 📝 **[Mandatory pre-message — the agent reply MUST expand this rule explicitly.]** When the user request contains only `QuotaId` OR `WorkspaceId` (or only mentions a quota name / workspace name in natural language while omitting the other half), the agent's text reply MUST contain the following three items in full — none may be omitted:
>
> 1. **Expand the pairing rule in plain English**: explicitly write *"`CordonParameters` / `UncordonParameters`'s `QuotaId` and `WorkspaceId` MUST be paired — provide both (scoped) or omit both (unscoped). Setting only one causes the backend to reject with `"both quota id and workspace id should be provided"`."* Do NOT merely link to this file / put the rule in a footnote / reference the path with a one-liner.
> 2. **Provide one complete legal payload alternative** (either the scoped version with the missing half filled in, or the unscoped version with both fields removed; one of the two, or both listed) so the user can choose one and proceed. The example MUST be directly copy-pasteable JSON, never a placeholder.
> 3. **State explicitly**: "Until you select a payload, I will not enter Resolved Plan, will not assemble the JSON, will not call `operate-node`, and will not let the backend reject."
>
> Selecting an alternative ≠ authorisation to execute: even if the user replies "use the first alternative" or fills in the missing half on the next turn, the agent MUST still complete the `CONFIRM-NODE-OP <NODE_ID>` token gate (per the SKILL.md §6.4 confirmation protocol) before invoking `operate-node`. The pre-message + alternative-selection are **preparation steps**, not **execution authorisation**.

> ⛔️ **[Alternative payloads do NOT authorise execution.]** Even if the agent presents multiple legal payloads in the pre-message (scoped / unscoped / different `Comment` / different sub-product subsets) and the user picks one, the `operate-node` call is STILL gated behind the `CONFIRM-NODE-OP <NODE_ID>` token. Alternatives are parameter convergence; the token unlocks execution. Any "user picked alternative A, so I'll just execute A" shortcut is unauthorised.

## DrainParameters

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `PodNames` | `[]string` | optional | Restrict eviction to listed pod names. Empty = all eligible pods. |
| `PodFromSubProducts` | `[]string` | optional | Restrict by sub-product. Allowed: `DLC` / `DSW` / `EAS` / `Tensorboard`. Other values → `"invalid production type"`. |

> 🚫 **`Force` is NOT exposed by this skill — backend Ops allowlist only.**
>
> `DrainParameters.Force` is controlled by the PAI backend Ops (operator) allowlist. This skill does NOT expose this field, does NOT accept it from the user, and will NEVER write `"Force": true` into any payload. Even if the user re-requests Force drain after submitting `CONFIRM-NODE-OP`, the agent MUST refuse again (the token only unlocks non-Force drain).
>
> When the user requests a Force drain (including "force drain", "clean up the stuck Terminating pods", "drain --force", "the eviction failed, try once more with force", or any variant), the agent's reply MUST explicitly state:
>
> 1. **This skill does not expose the `Force` field** — this is not a missing-parameter situation; it is a backend Ops allowlist boundary.
> 2. **The only escalation paths (three-way)** — there is no in-skill / `kubectl drain --force` / SSH `kill -9` / node-level direct-access substitute:
>    - **Platform Ops team** (contact directly)
>    - **Lingjun ops ticket** (file a ticket; Ops will go through the allowlist approval)
>    - **Account manager** (escalate to the Ops side via your account manager)
> 3. **What this skill can still do during the meantime** — read-only checks plus the regular (non-Force) drain alternative are still gated by the `CONFIRM-NODE-OP <NODE_ID>` token (per the SKILL.md §6.4 confirmation protocol).
>
> The agent MUST NOT, in any form (including by-the-way / FYI / parenthetical asides), hint that the user can run `kubectl drain --force` themselves / SSH into the node to clean up pods / hit an internal API via `curl` / any other "bypass the skill boundary" approach.

## CLI examples

> All examples below are business API commands and MUST be invoked with the per-command `--user-agent` flag specified in SKILL.md §0. The flag is omitted from the samples for readability — the agent MUST append it on every actual invocation.

```bash
# Cordon — scoped (Quota+Workspace together)
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Cordon \
  --operation-parameters '{"CordonParameters":{"QuotaId":"${QUOTA_ID}","WorkspaceId":"${WORKSPACE_ID}","Comment":"maintenance"}}'

# Cordon — unscoped (omit BOTH)
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Cordon \
  --operation-parameters '{"CordonParameters":{"Comment":"maintenance"}}'

# Uncordon — scoped
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Uncordon \
  --operation-parameters '{"UncordonParameters":{"QuotaId":"${QUOTA_ID}","WorkspaceId":"${WORKSPACE_ID}"}}'

# Drain — evict eligible pods, then cordon
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Drain \
  --operation-parameters '{"DrainParameters":{"PodFromSubProducts":["DLC","DSW"]}}'
```

**Permission**: `pai:UpdateResourceGroup` on the node's ResourceGroup **OR** `pai:UpdateQuota` on the root Quota (backend OR).
